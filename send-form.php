<?php
declare(strict_types=1);

const CLUB_EMAIL_FALLBACK = 'info@hkbrezno.sk';
const FROM_EMAIL_FALLBACK = 'no-reply@hkbrezno.sk';
const MAX_REQUESTS_PER_HOUR = 5;
const MAX_REQUEST_BYTES = 20000;

function security_headers(): void
{
    header('Content-Type: text/html; charset=UTF-8');
    header('Cache-Control: no-store');
    header('Content-Security-Policy: default-src \'none\'; style-src \'unsafe-inline\'; img-src \'self\' data:; base-uri \'none\'; form-action \'none\'; frame-ancestors \'none\'');
    header('Referrer-Policy: no-referrer');
    header('Permissions-Policy: camera=(), microphone=(), geolocation=()');
    header('X-Content-Type-Options: nosniff');
    header('X-Frame-Options: DENY');
    header('X-XSS-Protection: 0');
}

security_headers();

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
    if (($_SERVER['SERVER_PORT'] ?? '') === '443') {
        return true;
    }
    if (getenv('HK_TRUST_PROXY') === '1'
        && strtolower((string) ($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '')) === 'https') {
        return true;
    }
    return false;
}

function allowed_hosts(): array
{
    $configured = getenv('HK_ALLOWED_HOSTS');
    $hosts = $configured !== false && trim($configured) !== ''
        ? explode(',', $configured)
        : ['hkbrezno.sk', 'www.hkbrezno.sk', 'novyweb.smartitbiz.com'];
    return array_values(array_filter(array_map(static function ($host) {
        return strtolower(trim($host));
    }, $hosts)));
}

function validate_request_origin(): void
{
    $fetchSite = strtolower((string) ($_SERVER['HTTP_SEC_FETCH_SITE'] ?? ''));
    if ($fetchSite === 'cross-site') {
        respond(403, 'Požiadavka bola zamietnutá', 'Formulár je možné odoslať iba z webu HK Brezno.');
    }

    $source = (string) ($_SERVER['HTTP_ORIGIN'] ?? $_SERVER['HTTP_REFERER'] ?? '');
    $host = strtolower((string) parse_url($source, PHP_URL_HOST));
    $scheme = strtolower((string) parse_url($source, PHP_URL_SCHEME));
    if ($source === '' || $host === '' || $scheme !== 'https' || !in_array($host, allowed_hosts(), true)) {
        respond(403, 'Požiadavka bola zamietnutá', 'Nepodarilo sa overiť pôvod odoslania formulára.');
    }
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
    $handle = fopen($file, 'c+');
    if ($handle === false || !flock($handle, LOCK_EX)) {
        respond(503, 'Skúste neskôr', 'Formulár sa momentálne nedá bezpečne spracovať. Skúste to, prosím, neskôr.');
    }
    $raw = stream_get_contents($handle);
    $decoded = json_decode($raw ?: '{}', true);
    if (is_array($decoded)) {
        $data = $decoded;
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

    $ipKey = hash('sha256', $ip . (getenv('HK_RATE_LIMIT_SALT') ?: 'hkbrezno-form'));
    $hits = $data[$ipKey] ?? [];
    if (count($hits) >= MAX_REQUESTS_PER_HOUR) {
        flock($handle, LOCK_UN);
        fclose($handle);
        respond(429, 'Skúste neskôr', 'Formulár bol z tejto adresy odoslaný príliš veľakrát. Skúste to, prosím, neskôr.');
    }

    $hits[] = $now;
    $data[$ipKey] = $hits;
    rewind($handle);
    ftruncate($handle, 0);
    fwrite($handle, json_encode($data));
    fflush($handle);
    flock($handle, LOCK_UN);
    fclose($handle);
}

function mail_header_value(string $value): string
{
    return str_replace(["\r", "\n"], '', $value);
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    header('Allow: POST');
    respond(405, 'Nepovolená požiadavka', 'Formulár je možné odoslať iba metódou POST.');
}

if (!is_https_request()) {
    respond(400, 'Vyžaduje sa HTTPS', 'Prihlášku je možné odoslať až po zapnutí HTTPS na demo alebo produkčnej doméne.');
}

$requestLength = (int) ($_SERVER['CONTENT_LENGTH'] ?? 0);
if ($requestLength <= 0 || $requestLength > MAX_REQUEST_BYTES) {
    respond(413, 'Neplatná veľkosť požiadavky', 'Odoslané údaje sú prázdne alebo príliš veľké.');
}

$contentType = strtolower(trim(explode(';', (string) ($_SERVER['CONTENT_TYPE'] ?? ''))[0]));
if ($contentType !== 'application/x-www-form-urlencoded') {
    respond(415, 'Nepodporovaný formát', 'Formulár bol odoslaný v nepodporovanom formáte.');
}

validate_request_origin();

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

$allowedCategories = ['Prípravka U8', 'Mladší žiaci', 'Starší žiaci', 'Dorast'];
if (!in_array($category, $allowedCategories, true)) {
    respond(422, 'Neplatná kategória', 'Vyberte, prosím, jednu z ponúkaných kategórií.');
}

$allowedExperience = ['áno', 'nie', 'začiatočník'];
if (!in_array($experience, $allowedExperience, true)) {
    respond(422, 'Neplatná skúsenosť', 'Vyberte, prosím, jednu z ponúkaných možností.');
}

if (!preg_match('/^[0-9 +().-]{7,24}$/', $phone)) {
    respond(422, 'Neplatný telefón', 'Skontrolujte, prosím, telefónne číslo.');
}

$birth = DateTime::createFromFormat('Y-m-d', $birthDate);
if (!$birth || $birth->format('Y-m-d') !== $birthDate || $birth > new DateTime('today')) {
    respond(422, 'Neplatný dátum', 'Dátum narodenia musí byť zadaný vo formáte z formulára.');
}

if (field('consent_gdpr') !== '1') {
    respond(422, 'Chýba súhlas', 'Na odoslanie prihlášky je potrebný súhlas so spracovaním osobných údajov.');
}

$requestId = 'HK-' . gmdate('Ymd') . '-' . strtoupper(substr(bin2hex(random_bytes(3)), 0, 6));
$clubEmail = getenv('HK_FORM_TO') ?: CLUB_EMAIL_FALLBACK;
$fromEmail = getenv('HK_FORM_FROM') ?: FROM_EMAIL_FALLBACK;
if (!filter_var($clubEmail, FILTER_VALIDATE_EMAIL) || !filter_var($fromEmail, FILTER_VALIDATE_EMAIL)) {
    respond(500, 'Chyba konfigurácie', 'Kontaktný formulár nie je správne nakonfigurovaný.');
}

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
