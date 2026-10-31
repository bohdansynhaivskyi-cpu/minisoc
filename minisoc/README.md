# MiniSOC

Ein kleines Django-Projekt, das Grundprinzipien der IT-Sicherheit an einem lauffähigen Beispiel zeigt:
**Anmeldung mit MFA**, **Event-Sammlung mit Alarmregel (SIEM-Prinzip)**, **Endpoint-Compliance**,
**OWASP-Schutzmaßnahmen** und **Backup/Recovery**.

> **Wichtiger Hinweis:** MiniSOC ist ein Lern- und Demonstrationsprojekt. EDR-Status und Endpoint-Daten
> sind simuliert, und das Projekt ersetzt keines der echten Produkte (Entra ID, Intune, Defender,
> Sentinel, Splunk, CrowdStrike, Nessus …). Es zeigt, dass die dahinterliegenden **Konzepte** verstanden sind.

## Inhaltsverzeichnis

1. [Funktionsüberblick](#1-funktionsüberblick)
2. [Projektstruktur und Datenfluss](#2-projektstruktur-und-datenfluss)
3. [Installation und Start](#3-installation-und-start)
4. [Erster Rundgang](#4-erster-rundgang)
5. [Funktionen im Detail](#5-funktionen-im-detail)
6. [OWASP Top 10 im Code](#6-owasp-top-10-im-code)
7. [Zuordnung zu echten Produkten](#7-zuordnung-zu-echten-produkten)
8. [Tests](#8-tests)
9. [Konfiguration und Produktionshinweise](#9-konfiguration-und-produktionshinweise)
10. [Fehlerbehebung](#10-fehlerbehebung)
11. [Grenzen und Erweiterungen](#11-grenzen-und-erweiterungen)
12. [Glossar](#12-glossar)

---

## 1. Funktionsüberblick

| Bereich | Was die App macht |
|---|---|
| IAM / MFA | Login mit Benutzername und Passwort, danach Zweitfaktor per TOTP (Authenticator-App). Rollenbasierte Rechte. Ohne bestandene MFA ist nichts erreichbar. |
| SIEM-Prinzip | Anmelde- und MFA-Ereignisse werden als Events gespeichert. Eine Korrelationsregel erkennt Brute-Force-Muster und erzeugt Alerts. |
| Endpoint-Schutz | Endpoints werden gegen Compliance-Regeln geprüft (EDR läuft, Festplatte verschlüsselt, Patchstand aktuell). |
| OWASP-Awareness | Schutzmaßnahmen gegen die typischen Webrisiken sind im Code umgesetzt und kommentiert (siehe Abschnitt 6). |
| Backup / Recovery | Backup mit Prüfsumme und Rotation, Wiederherstellung mit Integritätsprüfung. |

Technik: Python 3.10+ (getestet mit 3.12), Django 5.2 oder neuer (getestet mit 6.1), SQLite,
`pyotp` für TOTP, `qrcode` für den QR-Code. Keine weiteren Abhängigkeiten, kein JavaScript-Framework.

---

## 2. Projektstruktur und Datenfluss

```
minisoc/
├── manage.py
├── requirements.txt
├── minisoc/                  Projekt-Konfiguration
│   ├── settings.py           gehärtete Einstellungen (Umgebungsvariablen, Cookies, HTTPS …)
│   └── urls.py               Routen: Dashboard, Login, MFA, Alert bestätigen, Admin
└── soc/                      die eigentliche App
    ├── models.py             MFADevice, SecurityEvent, Alert, Endpoint
    ├── services.py           SIEM-Logik: Events speichern und korrelieren
    ├── signals.py            fängt Login/Login-Fehler von Django ab und schreibt Events
    ├── middleware.py         erzwingt MFA für alle eingeloggten Benutzer
    ├── views.py              Dashboard, MFA einrichten/prüfen, Alert bestätigen
    ├── admin.py              Admin-Oberfläche (Logs nur lesbar, MFA-Secrets nicht sichtbar)
    ├── templates/soc/        base, login, mfa, dashboard
    ├── management/commands/  seed_demo, backup_db, restore_db
    └── tests.py              7 automatische Tests
```

So fließen die Daten bei einem Login:

```
Browser ──POST /login/──► Django-Login ──► Signal (signals.py)
                                               │
                                               ▼
                                   record_event()  (services.py)
                                               │ speichert SecurityEvent
                                               ▼
                              correlate_bruteforce()  zählt Fehlversuche je IP
                                               │ ab 5 in 10 Minuten
                                               ▼
                                         Alert  ──► Dashboard
```

---

## 3. Installation und Start

### Voraussetzungen

- Python 3.10 oder neuer (`python --version`)
- Optional: VS Code mit der Erweiterung „Python“ von Microsoft
- Optional: eine Authenticator-App (Microsoft Authenticator, Google Authenticator, Aegis …)

### Schritte

Im Projektordner (dort, wo `manage.py` liegt) im Terminal:

```bash
# 1. Virtuelle Umgebung anlegen und aktivieren
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell
source .venv/bin/activate         # macOS / Linux

# 2. Abhängigkeiten installieren
pip install -r requirements.txt

# 3. Datenbank anlegen
python manage.py migrate

# 4. Demo-Daten erzeugen (gibt das Passwort für "analyst" aus – bitte notieren)
python manage.py seed_demo

# 5. Server starten
python manage.py runserver
```

Danach ist die App unter <http://127.0.0.1:8000/> erreichbar.

**VS Code:** Ordner über *Datei → Ordner öffnen* laden, das Terminal mit `Strg+Ö` öffnen und den
Interpreter aus `.venv` wählen (`Strg+Umschalt+P` → „Python: Select Interpreter“).

**Admin-Zugang (optional):** `python manage.py createsuperuser` (Passwort mindestens 12 Zeichen), dann
<http://127.0.0.1:8000/admin/>. Auch hier ist MFA Pflicht.

---

## 4. Erster Rundgang

1. Öffne <http://127.0.0.1:8000/>. Du wirst zur Anmeldung geleitet.
2. Melde dich mit `analyst` und dem Passwort aus `seed_demo` an.
3. **MFA einrichten:** Scanne den QR-Code mit der Authenticator-App und gib den 6-stelligen Code ein.
   Ohne Handy zeigt die Seite den Schlüssel auch als Text. Den Code erzeugst du dann so:
   `python -c "import pyotp; print(pyotp.TOTP('DEIN_SCHLUESSEL').now())"`
4. Das **Dashboard** zeigt nun:
   - einen offenen Alert (simulierter Brute-Force-Angriff von `203.0.113.7`),
   - vier Endpoints, davon zwei nicht konform,
   - die letzten Events, darunter den Benutzernamen `<script>alert(1)</script>` als harmlosen Text.
5. **Live-Demo der Alarmregel:** Melde dich ab und gib 5-mal ein falsches Passwort ein. Nach dem
   Wiedereinloggen siehst du einen neuen Alert für `127.0.0.1`.
6. Klicke bei einem Alert auf „Als bearbeitet markieren“. Er verschwindet aus der Liste.

Bei jedem weiteren Login fragt die App nur noch nach dem Code (Seite „Code bestätigen“).

---

## 5. Funktionen im Detail

### 5.1 IAM und MFA

**Ablauf**

1. Django authentifiziert Benutzername und Passwort. Passwörter liegen nur als Hash in der Datenbank (PBKDF2).
2. Die Middleware `MFARequiredMiddleware` prüft bei **jeder** Anfrage, ob die Session das Flag
   `mfa_verified` trägt. Falls nicht, wird zu `/mfa/setup/` (noch kein Gerät) oder `/mfa/verify/` umgeleitet.
   Ausgenommen sind nur Login, Logout, die beiden MFA-Seiten und `/static/`.
3. Der Code wird mit `pyotp` geprüft (TOTP, 6 Stellen, 30-Sekunden-Takt, ±1 Intervall Toleranz für Uhrenabweichung).
4. Bei Erfolg setzt die App `mfa_verified` in der Session. Beim Abmelden oder nach 30 Minuten verfällt die Session.

**Rollen und Rechte (RBAC)**

`seed_demo` legt die Gruppe **SOC Analyst** an mit den Rechten `view_securityevent`, `view_alert`,
`view_endpoint` und `change_alert`. Das Dashboard verlangt `view_securityevent`, das Bestätigen eines Alerts
`change_alert`. Wer angemeldet ist, aber das Recht nicht hat, bekommt „403 Forbidden“. Der Bestätigen-Button wird
nur angezeigt, wenn das Recht vorhanden ist.

**Bewusste Sicherheitsentscheidungen**

- *Deny by default:* Die Middleware sperrt alles, was nicht ausdrücklich erlaubt ist. So kann man MFA nicht
  umgehen, indem man direkt eine andere URL (z. B. `/admin/`) aufruft.
- *Kein erneutes Enrollment:* Hat ein Benutzer bereits ein bestätigtes MFA-Gerät, leitet `/mfa/setup/` einfach
  zum Dashboard. Sonst könnte jemand mit gestohlenem Passwort ein neues Gerät registrieren und MFA aushebeln.
- *Fehlgeschlagene MFA-Codes* werden als Event protokolliert und zählen für die Brute-Force-Regel mit.
- *MFA-Secrets* sind im Admin nicht sichtbar (das Modell ist dort nicht registriert).

### 5.2 SIEM-Grundprinzip

Ein SIEM sammelt Logs aus vielen Quellen, normalisiert sie, korreliert sie nach Regeln und alarmiert.
MiniSOC bildet diese Kette in klein ab (`soc/services.py`, `soc/signals.py`):

| Schritt | Umsetzung |
|---|---|
| Sammeln | Django-Signale `user_logged_in` und `user_login_failed` plus die MFA-Prüfung rufen `record_event()` auf |
| Normalisieren | Alle Ereignisse landen im gleichen Format: Zeit, Typ, Benutzername, IP |
| Korrelieren | `correlate_bruteforce()` zählt Fehlversuche (`LOGIN_FAIL` und `MFA_FAIL`) je IP |
| Alarmieren | Ab **5 Fehlversuchen in 10 Minuten** entsteht ein Alert der Stufe „Hoch“ |
| Reagieren | Ein Analyst markiert den Alert im Dashboard als bearbeitet |

**Event-Typen:** `LOGIN_OK`, `LOGIN_FAIL`, `MFA_OK`, `MFA_FAIL`.

**Schwellwerte ändern:** In `soc/services.py` die Konstanten `THRESHOLD` (Anzahl) und `WINDOW` (Zeitfenster) anpassen.

**Doppelte Alerts vermeiden:** Hat die IP im Zeitfenster schon einen Alert ausgelöst, entsteht kein zweiter.

**Logging-Grundsätze (OWASP A09):** Es werden Benutzername und IP gespeichert, aber nie Passwörter oder MFA-Codes.
Die IP stammt ausschließlich aus `REMOTE_ADDR`, weil Header wie `X-Forwarded-For` ein Angreifer selbst setzen kann.
Im Admin sind Security-Events nur lesbar (kein Anlegen, Ändern, Löschen), damit niemand Spuren verwischen kann.

### 5.3 Endpoint-Compliance (EDR-/Intune-Gedanke)

Das Modell `Endpoint` beschreibt ein Gerät mit `hostname`, `os`, `edr_running`, `disk_encrypted` und `last_patch`.
Ein Gerät gilt als **konform**, wenn:

- der EDR-Agent läuft,
- die Festplatte verschlüsselt ist,
- der letzte Patch höchstens 30 Tage zurückliegt (`MAX_PATCH_AGE_DAYS`).

Das Dashboard zeigt pro Gerät den Status und die konkreten Auffälligkeiten. Die Demo-Daten:

| Host | System | Ergebnis |
|---|---|---|
| WS-001 | Windows 11 | konform |
| WS-014 | Windows 11 | Festplatte nicht verschlüsselt |
| LT-203 | macOS 15 | EDR-Agent läuft nicht, letzter Patch vor 45 Tagen |
| SRV-DB01 | Ubuntu 24.04 | konform |

Endpoints pflegst du im Admin unter `/admin/`. In einer echten Umgebung kämen diese Daten von einem Agenten
(Intune, Defender, CrowdStrike) statt von Hand.

### 5.4 Backup und Recovery

```bash
python manage.py backup_db
python manage.py restore_db backups/backup-20261031-152828.json
```

**Backup (`backup_db`)**

- Erzeugt `backups/backup-<Zeitstempel>.json` über Djangos `dumpdata` (ohne Sessions, Permissions, Content-Types).
- Berechnet eine SHA-256-Prüfsumme und legt sie als `.json.sha256` daneben.
- Setzt Dateirechte auf 600 und den Ordner auf 700 (unter Windows wirkungslos).
- **Rotation:** Es bleiben die letzten 7 Backups (`BACKUP_KEEP` in `settings.py`), ältere werden samt Prüfsumme gelöscht.

**Restore (`restore_db`)**

- Prüft zuerst, ob Backup- und Prüfsummen-Datei existieren und die Prüfsumme stimmt. Bei Abweichung **Abbruch**
  („defekt oder manipuliert“). Danach wird mit `loaddata` eingespielt.
- Getestet: Zurückspielen in dieselbe Datenbank und in eine frisch migrierte, leere Datenbank
  (Benutzer, Rolle samt Rechten, Events, Alerts und Endpoints stimmten danach überein).
- Für einen kompletten Rücksprung in einen früheren Zustand: `db.sqlite3` löschen, `python manage.py migrate`,
  dann `restore_db`. Beim Einspielen in eine bestehende Datenbank werden Objekte mit gleicher ID überschrieben,
  neuere Objekte aber nicht gelöscht.

**Prinzipien, die dahinterstehen**

1. Regelmäßig sichern (z. B. per Cron oder Aufgabenplanung).
2. Mehrere Generationen aufbewahren (Rotation).
3. Integrität prüfen (Prüfsumme).
4. Backups schützen. Die Datei enthält Passwort-Hashes und MFA-Secrets, deshalb eingeschränkte Rechte und in Produktion Verschlüsselung.
5. **Restore regelmäßig testen.** Ein ungetestetes Backup ist keine Garantie.
6. 3-2-1-Regel: 3 Kopien, auf 2 verschiedenen Medien, 1 Kopie extern oder offline.

---

## 6. OWASP Top 10 im Code

Bezug: OWASP Top 10 in der Ausgabe 2021.

| Risiko | Maßnahme im Projekt | Wo |
|---|---|---|
| A01 Broken Access Control | `login_required`, `permission_required`, MFA-Middleware (deny by default), Logs im Admin nur lesbar | `views.py`, `middleware.py`, `admin.py` |
| A02 Cryptographic Failures | Passwort-Hashing, Secrets aus Umgebungsvariablen, in Produktion HTTPS-Zwang, HSTS, Secure-Cookies | `settings.py` |
| A03 Injection | ORM mit parametrisierten Queries statt SQL-Strings, Template-Auto-Escaping gegen XSS (Demo: `<script>`-Benutzername wird als Text angezeigt) | `views.py`, Templates |
| A04 Insecure Design | Deny by default, kein erneutes MFA-Enrollment, Alarmregel als Teil des Designs | `middleware.py`, `views.py`, `services.py` |
| A05 Security Misconfiguration | `DEBUG` per Umgebungsvariable, `ALLOWED_HOSTS`, `X_FRAME_OPTIONS = DENY`, Prüfung mit `check --deploy` | `settings.py` |
| A06 Vulnerable Components | Abhängigkeiten minimal halten und mit `pip-audit` auf bekannte Schwachstellen prüfen | `requirements.txt` |
| A07 Identification and Authentication Failures | Mindestlänge 12 Zeichen, Passwortprüfungen, MFA, Session-Timeout 30 Minuten, Brute-Force-Alert | `settings.py`, `services.py` |
| A08 Software and Data Integrity Failures | CSRF-Token bei jedem POST (auch Logout), Prüfsummen für Backups | Templates, `backup_db.py` |
| A09 Security Logging and Monitoring Failures | Security-Events, Alerts, keine sensiblen Daten im Log, unveränderliche Logs im Admin | `services.py`, `admin.py` |
| A10 Server-Side Request Forgery | Nicht relevant, die App ruft keine vom Benutzer vorgegebenen URLs auf | – |

**Selbst ausprobieren**

```bash
# Konfigurationsprüfung wie bei einem Scan (benötigt einen langen, zufälligen Schlüssel)
DJANGO_DEBUG=0 DJANGO_SECRET_KEY="$(python -c 'import secrets;print(secrets.token_urlsafe(60))')" python manage.py check --deploy

# Bekannte Schwachstellen in Abhängigkeiten finden (A06)
pip install pip-audit
pip-audit -r requirements.txt
```

Unter Windows PowerShell setzt man die Variablen vorher mit `$env:DJANGO_DEBUG="0"` und `$env:DJANGO_SECRET_KEY="..."`.

---

## 7. Zuordnung zu echten Produkten

| Produkt (Beispiel) | Konzept | Umsetzung in MiniSOC | Was das echte Produkt zusätzlich kann |
|---|---|---|---|
| Microsoft Entra ID | Identitäten, MFA, Rollen | Django-Auth, TOTP, Gruppen und Rechte | Conditional Access, SSO, Passkeys, Identity Protection |
| Microsoft Intune | Geräteverwaltung und Compliance | `Endpoint` mit Compliance-Regeln | Richtlinien aufs Gerät ausrollen, Geräte sperren oder löschen |
| Microsoft Defender / CrowdStrike | Endpoint-Schutz, EDR | Feld `edr_running` als Statusmeldung | Verhaltensanalyse, Isolierung infizierter Geräte, Threat Hunting |
| Microsoft Sentinel / Splunk | SIEM | Events, Korrelationsregel, Alerts | Logs aus Hunderten Quellen, Abfragesprache (KQL, SPL), Playbooks, Machine Learning |
| Nessus / Tenable / Qualys | Schwachstellenscan | `check --deploy`, `pip-audit` | Netzwerk- und Systemscans, CVE-Datenbanken, Priorisierung |
| Palo Alto (Firewall) | Netzwerkschutz | nicht abgebildet | Segmentierung, Traffic-Inspektion, Threat Prevention |

---

## 8. Tests

```bash
python manage.py test
```

| Test | Prüft |
|---|---|
| `test_bruteforce_creates_exactly_one_alert` | 7 Fehlversuche erzeugen genau einen Alert |
| `test_few_failures_create_no_alert` | 4 Fehlversuche lösen noch keinen Alert aus |
| `test_dashboard_blocked_without_mfa` | Ohne MFA wird zur Code-Eingabe umgeleitet |
| `test_wrong_code_is_logged_and_denied` | Falscher Code wird geloggt und gewährt keinen Zugriff |
| `test_valid_code_grants_access` | Gültiger Code öffnet das Dashboard |
| `test_no_reenrollment_when_mfa_exists` | MFA-Secret lässt sich nicht überschreiben |
| `test_roundtrip_and_tamper_detection` | Backup und Restore klappen, manipulierte Datei wird abgelehnt |

---

## 9. Konfiguration und Produktionshinweise

| Umgebungsvariable | Bedeutung | Standard |
|---|---|---|
| `DJANGO_DEBUG` | `1` = Entwicklung, `0` = Produktion | `1` |
| `DJANGO_SECRET_KEY` | geheimer Schlüssel, in Produktion Pflicht | nur bei Debug ein Entwicklungswert |
| `DJANGO_ALLOWED_HOSTS` | erlaubte Hostnamen, durch Komma getrennt | `localhost,127.0.0.1` |

Weitere Einstellungen in `minisoc/settings.py`: `SESSION_COOKIE_AGE` (Session-Dauer), `BACKUP_DIR`, `BACKUP_KEEP`.

**Wichtig:** Mit `DJANGO_DEBUG=0` erzwingt die App HTTPS (Weiterleitung, Secure-Cookies, HSTS). Lokal über
`http://127.0.0.1:8000` funktioniert das deshalb nicht. Dieser Modus ist für `check --deploy` und für den Betrieb
hinter einem HTTPS-fähigen Webserver gedacht. Für echten Betrieb außerdem: einen Produktions-Webserver
(z. B. gunicorn hinter nginx) statt `runserver`, statische Dateien ausliefern und eine robustere Datenbank wie PostgreSQL nutzen.

---

## 10. Fehlerbehebung

| Problem | Lösung |
|---|---|
| `python` wird nicht gefunden | Unter Windows `py` statt `python` versuchen, unter macOS/Linux `python3` |
| PowerShell blockiert das Aktivieren der Umgebung | Einmalig `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `ModuleNotFoundError: django` | Umgebung nicht aktiv oder `pip install -r requirements.txt` vergessen |
| Das Passwort von `analyst` ist vergessen | `python manage.py changepassword analyst` (mindestens 12 Zeichen) |
| MFA-Code wird immer abgelehnt | Uhrzeit von Handy und Rechner prüfen, die Codes hängen von der genauen Zeit ab |
| Handy mit MFA verloren | Im Admin als Superuser keine Option vorhanden (Absicht). Zurücksetzen per Shell: `python manage.py shell -c "from soc.models import MFADevice; MFADevice.objects.filter(user__username='analyst').delete()"` |
| Seite ohne Styling im Admin bei `DEBUG=0` | `runserver` liefert statische Dateien nur im Debug-Modus aus |
| „403 Forbidden“ nach dem Login | Benutzer hat nicht das Recht `view_securityevent` (Gruppe „SOC Analyst“ zuweisen) |

---

## 11. Grenzen und Erweiterungen

**Bekannte Vereinfachungen**

- Keine Kontosperre nach Fehlversuchen und kein Rate-Limiting (es wird nur erkannt und alarmiert).
- Kein Replay-Schutz: Ein TOTP-Code lässt sich innerhalb seines Zeitfensters mehrfach verwenden.
- MFA-Secrets und Backups liegen unverschlüsselt vor.
- Die Doppel-Alert-Prüfung vergleicht die IP als Textbestandteil; für Produktion wäre ein eigenes IP-Feld am Alert sauberer.
- Keine Wiederherstellungscodes für den Fall eines verlorenen Handys.
- Endpoint-Daten werden manuell gepflegt, nicht von einem Agenten gemeldet.

**Sinnvolle nächste Schritte**

- Kontosperre und Rate-Limiting beim Login
- Weitere Korrelationsregeln, z. B. erfolgreicher Login kurz nach vielen Fehlversuchen oder viele verschiedene Benutzer von einer IP (Password Spraying)
- Agent-API: Endpoints melden ihren Status per authentifiziertem POST
- Verschlüsselte Backups und automatische Zeitplanung
- Benachrichtigung bei Alerts per E-Mail
- PostgreSQL, Docker und eine Deployment-Anleitung

---

## 12. Glossar

| Begriff | Bedeutung |
|---|---|
| IAM | Identity and Access Management: Verwaltung von Identitäten und ihren Zugriffsrechten |
| MFA | Multi-Faktor-Authentifizierung: Anmeldung mit mindestens zwei unabhängigen Faktoren (Wissen, Besitz, Merkmal) |
| TOTP | Time-based One-Time Password: zeitabhängiger Einmalcode, wie ihn Authenticator-Apps erzeugen |
| RBAC | Role-Based Access Control: Rechte werden Rollen zugeordnet, nicht einzelnen Personen |
| EDR | Endpoint Detection and Response: Schutz und Überwachung von Endgeräten mit Erkennung und Reaktion |
| SIEM | Security Information and Event Management: zentrales Sammeln, Korrelieren und Alarmieren von Sicherheitsereignissen |
| Korrelationsregel | Regel, die mehrere Einzelereignisse zu einem Verdacht verknüpft |
| Compliance | Einhaltung festgelegter Sicherheitsvorgaben, hier für Endgeräte |
| Brute Force | Systematisches Durchprobieren von Passwörtern oder Codes |
| CSRF | Cross-Site Request Forgery: Angriff, bei dem eine fremde Seite im Namen des Benutzers Aktionen auslöst |
| XSS | Cross-Site Scripting: Einschleusen von Skriptcode in eine Webseite |
| Rotation (Backup) | Alte Backups werden nach festem Schema gelöscht, damit nur die letzten N bleiben |
| Deny by default | Alles ist verboten, was nicht ausdrücklich erlaubt ist |
