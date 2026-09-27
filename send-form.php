<?php
declare(strict_types=1);

const CLUB_EMAIL_FALLBACK = 'info@hkbrezno.sk';
const MAX_REQUESTS_PER_HOUR = 5;

function respond(int $status, string $title, string $message): void
{
    http_response_code($status);
    $safeTitle = htmlspecialchars($title, ENT_QUOTES, 'UTF-8');
    $safeMessage = htmlspecialchars($message, ENT_QUOTES, 'UTF-8');
    echo '<!doctype html><html lang="sk"><head><meta charset="utf-8">';
    echo '<meta name="viewport" content="width=device-width, initial-scale=1">';
    echo '<title>' . $safeTitle . ' | HK Brezno</title>';
    echo '<style>body{margin:0;background:#e7ecf1;color:#0b1b33;font-family:system-ui,-apple-system,Segoe UI,sans-serif}main{max-width:720px;margin:8vh auto;background:#fff;padding:34px 28px;border-top:4px solid #ce1126;box-shadow:0 14px 34px rgba(11,27,51,.12)}h1{margin:0 0 12px;font-size:30px}p{font-size:18px;line-height:1.6}a{color:#ce1126;font-weight:700}</style>';
    echo '</head><body><main><h1>' . $safeTitle . '</h1><p>' . $safeMessage . '</p>';
    echo '<p><a href="./">Späť na web HK Brezno</a></p></main></body></html>';
    exit;
}

function is_https_request(): bool
{
    if (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') {
        return true;
    }
    if (($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https') {
        return true;
    }
    return false;
}

function field(string $key): string
{
    $value = $_POST[$key] ?? '';
    if (is_array($value)) {
        $value = '';
    }
    $value = trim((string) $value);
    $value = str_replace(["\r", "\n"], ' ', $value);
    return strip_tags($value);
}

function require_field(string $key, string $label, int $maxLength = 200): string
{
    $value = field($key);
    if ($value === '') {
        respond(422, 'Chýba údaj', 'Pole "' . $label . '" je povinné.');
    }
    if (strlen($value) > $maxLength) {
        respond(422, 'Príliš dlhý údaj', 'Pole "' . $label . '" je príliš dlhé.');
    }
    return $value;
}

function rate_limit(string $ip): void
{
    $file = sys_get_temp_dir() . '/hkbrezno-form-rate.json';
    $now = time();
    $windowStart = $now - 3600;
    $data = [];

    if (is_file($file)) {
        $raw = file_get_contents($file);
        $decoded = json_decode($raw ?: '{}', true);
        if (is_array($decoded)) {
            $data = $decoded;
        }
    }

    foreach ($data as $key => $timestamps) {
        if (!is_array($timestamps)) {
            unset($data[$key]);
            continue;
        }
        $data[$key] = array_values(array_filter($timestamps, static function ($ts) use ($windowStart) {
            return is_int($ts) && $ts >= $windowStart;
        }));
        if (!$data[$key]) {
            unset($data[$key]);
        }
    }

    $hits = $data[$ip] ?? [];
    if (count($hits) >= MAX_REQUESTS_PER_HOUR) {
        respond(429, 'Skúste neskôr', 'Formulár bol z tejto adresy odoslaný príliš veľakrát. Skúste to, prosím, neskôr.');
    }

    $hits[] = $now;
    $data[$ip] = $hits;
    file_put_contents($file, json_encode($data), LOCK_EX);
}

function mail_header_value(string $value): string
{
    return str_replace(["\r", "\n"], '', $value);
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    respond(405, 'Nepovolená požiadavka', 'Formulár je možné odoslať iba metódou POST.');
}

if (!is_https_request()) {
    respond(400, 'Vyžaduje sa HTTPS', 'Prihlášku je možné odoslať až po zapnutí HTTPS na demo alebo produkčnej doméne.');
}

if (field('website') !== '') {
    respond(200, 'Ďakujeme', 'Vaša žiadosť bola prijatá a odoslaná na spracovanie HK Brezno. Potvrdenie sme vám zaslali aj e-mailom.');
}

$ip = $_SERVER['REMOTE_ADDR'] ?? 'unknown';
rate_limit($ip);

$childFirstName = require_field('child_first_name', 'Meno dieťaťa', 80);
$childLastName = require_field('child_last_name', 'Priezvisko dieťaťa', 80);
$birthDate = require_field('child_birth_date', 'Dátum narodenia', 20);
$category = require_field('category', 'Kategória', 80);
$parentName = require_field('parent_name', 'Rodič', 120);
$parentEmail = require_field('parent_email', 'E-mail', 160);
$phone = require_field('phone', 'Telefón', 40);
$experience = require_field('skating_experience', 'Skúsenosť s korčuľovaním', 40);
$note = field('note');
$note = substr($note, 0, 1200);

if (!filter_var($parentEmail, FILTER_VALIDATE_EMAIL)) {
    respond(422, 'Neplatný e-mail', 'Skontrolujte, prosím, e-mailovú adresu zákonného zástupcu.');
}

if (!preg_match('/^[0-9 +().-]{7,24}$/', $phone)) {
    respond(422, 'Neplatný telefón', 'Skontrolujte, prosím, telefónne číslo.');
}

$birth = DateTime::createFromFormat('Y-m-d', $birthDate);
if (!$birth || $birth->format('Y-m-d') !== $birthDate) {
    respond(422, 'Neplatný dátum', 'Dátum narodenia musí byť zadaný vo formáte z formulára.');
}

if (field('consent_gdpr') !== '1') {
    respond(422, 'Chýba súhlas', 'Na odoslanie prihlášky je potrebný súhlas so spracovaním osobných údajov.');
}

$requestId = 'HK-' . gmdate('Ymd') . '-' . strtoupper(substr(bin2hex(random_bytes(3)), 0, 6));
$clubEmail = getenv('HK_FORM_TO') ?: CLUB_EMAIL_FALLBACK;
$fromEmail = 'no-reply@' . ($_SERVER['HTTP_HOST'] ?? 'hkbrezno.sk');

$lines = [
    'Nová žiadosť z formulára HK Brezno',
    'Referencia: ' . $requestId,
    '',
    'Dieťa: ' . $childFirstName . ' ' . $childLastName,
    'Dátum narodenia: ' . $birthDate,
    'Kategória: ' . $category,
    'Skúsenosť s korčuľovaním: ' . $experience,
    '',
    'Zákonný zástupca: ' . $parentName,
    'E-mail: ' . $parentEmail,
    'Telefón: ' . $phone,
    '',
    'Poznámka: ' . ($note !== '' ? $note : '-'),
    '',
    'IP adresa: ' . $ip,
];

$headers = [
    'From: HK Brezno <' . mail_header_value($fromEmail) . '>',
    'Reply-To: ' . mail_header_value($parentEmail),
    'Content-Type: text/plain; charset=UTF-8',
];

$clubSent = mail(
    $clubEmail,
    'Nová prihláška HK Brezno ' . $requestId,
    implode("\n", $lines),
    implode("\r\n", $headers)
);

$parentMessage = implode("\n", [
    'Dobrý deň,',
    '',
    'vaša žiadosť bola prijatá a odoslaná na spracovanie HK Brezno.',
    'Referencia žiadosti: ' . $requestId,
    '',
    'Klub vás bude kontaktovať s ďalšími informáciami.',
    '',
    'HK Brezno',
]);

$parentSent = mail(
    $parentEmail,
    'Potvrdenie prijatia žiadosti HK Brezno ' . $requestId,
    $parentMessage,
    implode("\r\n", [
        'From: HK Brezno <' . mail_header_value($fromEmail) . '>',
        'Content-Type: text/plain; charset=UTF-8',
    ])
);

if (!$clubSent || !$parentSent) {
    respond(500, 'Odoslanie zlyhalo', 'Pri odosielaní e-mailu nastala chyba. Skúste to, prosím, neskôr alebo kontaktujte klub priamo.');
}

respond(200, 'Prihláška odoslaná', 'Vaša žiadosť bola prijatá a odoslaná na spracovanie HK Brezno. Potvrdenie sme vám zaslali aj e-mailom. Referencia: ' . $requestId);
