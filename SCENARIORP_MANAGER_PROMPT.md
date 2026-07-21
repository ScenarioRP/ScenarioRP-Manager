# ScenarioRP Manager — AI Development Prompt

קרא את `docs/PROJECT_PHILOSOPHY.md` לפני כל שינוי ופעל לפיו.

## מטרת הפרויקט

יש לבנות אפליקציית ניהול מקומית בשם **ScenarioRP Manager**.

האפליקציה מיועדת לנהל סביבת פיתוח ניידת של שרת FiveM בשם `ScenarioRP`, כאשר כל הפרויקט עשוי להימצא על כונן USB או SSD חיצוני ולעבור בין מחשבים שונים.

האפליקציה תיכתב ב־Python עם PySide6.

המטרה היא ליצור כלי ניהול קטן, יציב, ברור ומודולרי — לא מערכת מורכבת מדי ולא סקריפט חד־פעמי.

---

# לפני כתיבת קוד

בצע קודם את השלבים הבאים:

1. סרוק את מבנה הפרויקט הקיים.
2. אתר את הנתיבים האמיתיים של:
   - `FXServer.exe`
   - תיקיית `txData`
   - `server.cfg`
   - Discord bot
   - ה־`.venv` של הבוט
   - `manager.ps1`
3. אל תניח שמות קבצים או נתיבים אם ניתן לזהות אותם מתוך הפרויקט.
4. הצג תכנון ארכיטקטורה קצר.
5. הצג רשימת קבצים שתיצור או תשנה.
6. הסבר את זרימת ההפעלה והעצירה.
7. בחר בין `QProcess` לבין `subprocess` והסבר את הבחירה.
8. המתן לאישור לפני כתיבת הקוד.

---

# פילוסופיית הפיתוח

- הקוד הוא מקור האמת.
- אין ליצור תיעוד שחוזר על מה שכבר ברור מהקוד.
- תיעוד צריך להסביר רק:
  - למה התקבלה החלטה מסוימת.
  - ממה צריך להיזהר.
  - החלטות מיוחדות של ScenarioRP.
- כל קובץ צריך להיות קצר, ממוקד ובעל אחריות ברורה.
- אין ליצור שכבות או abstractions שאין בהן צורך ממשי.
- יש להעדיף פתרון פשוט ויציב על פני מערכת מורכבת מדי.
- אין לכתוב את כל האפליקציה בקובץ אחד.

---

# מבנה מוצע

```text
ScenarioRP/
├── manager.ps1
├── docs/PROJECT_PHILOSOPHY.md
├── ScenarioRP-Manager/
│   ├── app.py
│   ├── config.json
│   ├── requirements.txt
│   ├── .env.example
│   ├── .gitignore
│   ├── .venv/
│   ├── core/
│   │   ├── config.py
│   │   ├── paths.py
│   │   ├── process.py
│   │   └── logging.py
│   ├── services/
│   │   ├── fxserver_service.py
│   │   ├── discord_bot_service.py
│   │   ├── txadmin_service.py
│   │   ├── database_service.py
│   │   ├── tailscale_service.py
│   │   ├── environment_service.py
│   │   └── backup_service.py
│   ├── models/
│   │   ├── process_status.py
│   │   └── environment_check.py
│   ├── ui/
│   │   ├── main_window.py
│   │   ├── styles.qss
│   │   └── widgets/
│   │       ├── status_card.py
│   │       ├── log_viewer.py
│   │       └── action_button.py
│   ├── logs/
│   └── state/
├── server/
│   └── FXServer.exe
├── txData/
├── ScenarioRP-Discord-Bots/
│   └── Server-Status/
│       ├── bot.py
│       └── .venv/
└── backups/
```

אפשר לשנות את המבנה אם יש סיבה טובה, אך יש להסביר אותה לפני השינוי.

---

# עקרונות ארכיטקטורה

## אחריות `MainWindow`

`MainWindow` אחראי רק על:

- הצגת מידע.
- חיבור Signals ו־Slots.
- קריאה ל־Services.
- עדכון ממשק המשתמש.

`MainWindow` לא אחראי על:

- הפעלת תהליכים ישירות.
- חיפוש נתיבים.
- גישה ל־MariaDB.
- גיבויים.
- ניתוח לוגים.
- לוגיקת Tailscale.

## Services

לכל מערכת יהיה Service נפרד.

דוגמה:

```python
class FXServerService:
    def start(self) -> None:
        ...

    def stop(self) -> None:
        ...

    def restart(self) -> None:
        ...

    def get_status(self) -> ProcessStatus:
        ...
```

אותו עיקרון יחול על:

- `DiscordBotService`
- `DatabaseService`
- `TailscaleService`
- `EnvironmentService`
- `BackupService`
- `TxAdminService`

---

# גרסת MVP

בשלב הראשון האפליקציה צריכה לכלול רק:

1. `Start All`
2. `Stop All`
3. `Restart All`
4. מצב חי של FXServer
5. מצב חי של Discord bot
6. פתיחת txAdmin בדפדפן
7. פתיחת תיקיית הלוגים
8. הצגת לוגים בתוך האפליקציה
9. `Safe Shutdown`
10. דרך אמינה לזהות רק את התהליכים שהאפליקציה הפעילה

אין לבנות עדיין:

- מערכת Plugins.
- התקנות אוטומטיות.
- MariaDB Portable.
- עדכוני Artifacts אוטומטיים.
- מערכת גיבויים מלאה.
- Eject פיזי של הכונן.

---

# סדר ההפעלה

כאשר לוחצים `Start All`:

1. בדוק שכל הנתיבים הדרושים קיימים.
2. בדוק שהתהליכים אינם כבר רצים.
3. הפעל את FXServer.
4. אמת שהתהליך אכן התחיל.
5. הפעל את Discord bot דרך ה־Python של ה־`.venv` שלו.
6. עדכן את ה־UI.
7. כתוב לוג ברור.

---

# סדר העצירה

כאשר לוחצים `Stop All`:

1. עצור קודם את FXServer.
2. המתן לסיום התהליך.
3. עצור את Discord bot.
4. נקה PID files ישנים או state לא תקין.
5. עדכן את ה־UI.
6. כתוב לוג ברור.

אין להשתמש בפקודה כללית שסוגרת כל תהליך בשם `FXServer`, `python` או `PowerShell`.

יש לזהות רק את התהליכים שהאפליקציה עצמה הפעילה.

---

# Safe Shutdown

צור כפתור בשם:

```text
Safe Shutdown
```

הוא צריך:

1. לעצור את FXServer.
2. לעצור את Discord bot.
3. לוודא שאין תהליך גיבוי פעיל.
4. לסגור קבצי לוג פתוחים.
5. להכין מקום להוספת MariaDB נייד בעתיד.
6. להציג הודעה:

```text
ScenarioRP is safe to close.
You may now eject the drive.
```

בשלב הראשון אין לבצע Eject פיזי של הכונן.

---

# ניהול תהליכים

העדף `QProcess` אם הוא מתאים, במיוחד אם הוא מאפשר:

- Signals עבור `stdout`.
- Signals עבור `stderr`.
- מעקב אחר מצב התהליך.
- קבלת PID.
- סגירה נקייה.
- הצגת פלט בזמן אמת.

אם משתמשים ב־`QProcess`:

- הסבר למה.
- שמור reference לתהליך.
- אל תאפשר ל־Garbage Collector למחוק אותו.
- קרא `stdout` ו־`stderr` בזמן אמת.
- הצג את הפלט ב־Log Viewer.
- כתוב את הפלט גם לקובצי לוג.

---

# לוגים

האפליקציה צריכה לכתוב לוגים אל:

```text
ScenarioRP-Manager/logs/manager.log
ScenarioRP-Manager/logs/fxserver.log
ScenarioRP-Manager/logs/discord-bot.log
```

פורמט מומלץ:

```text
2026-07-16 18:40:20 | INFO | FXServer | Process started with PID 1234
```

כל שורה תכלול:

- Timestamp
- Level
- Source
- Message

ה־Log Viewer ב־UI צריך לכלול:

- Auto Scroll
- Clear View
- Open Log File
- סינון לפי מקור
- סינון לפי רמת לוג

---

# ממשק משתמש

העיצוב צריך להיות:

- כהה.
- נקי.
- מודרני.
- ברור.
- ללא אפקטים מיותרים.

## Header

הצג:

- `ScenarioRP Manager`
- נתיב שורש הפרויקט
- מצב כללי

## Status Cards

צור כרטיסים עבור:

- FXServer
- Discord Bot
- txAdmin
- Database
- Tailscale

כל כרטיס יציג:

- `Running`
- `Stopped`
- `Error`
- `Unknown`
- PID, אם קיים
- זמן פעילות, אם אפשר
- הודעת מצב קצרה

## Actions

- `Start All`
- `Stop All`
- `Restart All`
- `Safe Shutdown`
- `Open txAdmin`
- `Open Project Folder`
- `Open Logs`

## Logs

הצג אזור מרכזי לצפייה בלוגים בזמן אמת.

---

# Config

אין להקשיח נתיבים בקוד.

יש ליצור `config.json`.

דוגמה:

```json
{
  "project_root": "..",
  "fxserver_exe": "server/FXServer.exe",
  "txdata_dir": "txData/ScenarioRP",
  "server_cfg": "txData/ScenarioRP/server.cfg",
  "discord_bot_dir": "ScenarioRP-Discord-Bots/Server-Status",
  "discord_bot_python": "ScenarioRP-Discord-Bots/Server-Status/.venv/Scripts/python.exe",
  "discord_bot_file": "ScenarioRP-Discord-Bots/Server-Status/bot.py",
  "txadmin_url": "http://127.0.0.1:40120",
  "logs_dir": "ScenarioRP-Manager/logs",
  "backups_dir": "backups"
}
```

כל הנתיבים היחסיים יחושבו ביחס לשורש הפרויקט.

האפליקציה חייבת לעבוד גם כאשר אות הכונן משתנה:

```text
C:
D:
E:
F:
```

אין להניח אות כונן קבועה.

שורש הפרויקט צריך להתגלות לפי המיקום של `manager.ps1` או תיקיית האפליקציה.

---

# Environment Check

צור Dialog או מסך בשם:

```text
Environment Check
```

הוא יבדוק:

- `FXServer.exe` קיים.
- `txData` קיימת.
- `server.cfg` קיים.
- Python של `.venv` קיים.
- קובץ הבוט קיים.
- פורט `40120` זמין או נמצא בשימוש צפוי.
- פורט `30120` פתוח מקומית.
- Tailscale מותקן.
- שירות MariaDB קיים.
- יש מקום פנוי בכונן.
- קיימות הרשאות כתיבה.
- מהי מערכת הקבצים של הכונן.

מודל מוצע:

```python
from dataclasses import dataclass

@dataclass
class EnvironmentCheck:
    name: str
    status: bool
    message: str
    severity: str
```

בגרסת MVP אין לתקן אוטומטית שום דבר.

יש רק להציג מה תקין ומה חסר.

---

# Tailscale

בשלב הראשון:

- בדוק אם `tailscale.exe` קיים.
- נסה להריץ `tailscale status`.
- הצג את כתובת ה־Tailscale המקומית.
- הצג האם קיימים Peers מחוברים.

אין לבצע:

- Login אוטומטי.
- Logout.
- שינוי הגדרות.
- שינוי DNS.
- שינוי Access Rules.

---

# Database

בשלב הראשון:

- בדוק אם שירות MariaDB רץ.
- בדוק אם ניתן להתחבר לפי ההגדרות.
- הצג את שם מסד הנתונים.
- הצג את גרסת MariaDB, אם אפשר.
- הצג `Running`, `Stopped`, `Connected` או `Failed`.

אין לבצע:

- מחיקת מסד.
- יצירת מסד אוטומטית.
- Migrations אוטומטיים.
- שינוי משתמשים.
- שינוי הרשאות.

אין לשמור סיסמה ישירות בקוד.

השתמש ב־`.env` או בקובץ הגדרות מקומי שלא נכנס ל־Git.

---

# Security

אין לשמור בתוך Git:

- Discord token
- MariaDB password
- FiveM Server Key
- Tailscale secrets
- סיסמאות אחרות

צור:

```text
.env.example
```

והוסף את `.env` ל־`.gitignore`.

האפליקציה צריכה להציג שגיאה ידידותית אם ערך סודי חסר.

---

# manager.ps1

`manager.ps1` יישאר בשורש הפרויקט.

התפקיד היחיד שלו:

1. למצוא את שורש הפרויקט.
2. למצוא את Python של ScenarioRP Manager.
3. להפעיל את `app.py`.
4. להציג הודעת שגיאה ברורה אם ה־`.venv` או האפליקציה חסרים.

דוגמה רעיונית:

```powershell
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = Join-Path $ProjectRoot "ScenarioRP-Manager\.venv\Scripts\python.exe"
$AppFile = Join-Path $ProjectRoot "ScenarioRP-Manager\app.py"

if (-not (Test-Path $PythonExe)) {
    throw "Manager Python was not found: $PythonExe"
}

if (-not (Test-Path $AppFile)) {
    throw "Manager app was not found: $AppFile"
}

& $PythonExe $AppFile
```

---

# Error Handling

אין להשתמש ב־`try/except` ריק.

כל שגיאה צריכה:

- להיכתב ללוג.
- להופיע ב־UI בצורה ידידותית.
- לשמור traceback בלוג, במידת הצורך.
- לא להפיל את כל האפליקציה אם רק Service אחד נכשל.

---

# Threading

אסור לחסום את ה־UI.

פעולות ארוכות, כגון:

- בדיקות סביבה.
- קריאת לוגים גדולים.
- גיבויים.
- בדיקות רשת.
- בדיקות Database.

צריכות לרוץ באמצעות:

- `QThread`
- `QRunnable`
- או מנגנון מתאים אחר.

אין להוסיף Threads לפעולות קצרות שאין בהן צורך.

---

# Testing

צור בדיקות לפחות עבור:

- חישוב נתיבים יחסיים.
- טעינת Config.
- זיהוי קובץ חסר.
- זיהוי State ישן של תהליך.
- Environment Checks בסיסיים.

אין לבצע Integration Test אמיתי ל־FXServer בשלב הראשון.

---

# README

צור README קצר שכולל:

- איך ליצור `.venv`.
- איך להתקין `requirements.txt`.
- איך להפעיל דרך `manager.ps1`.
- איך להגדיר `config.json`.
- איך להגדיר `.env`.
- מבנה הפרויקט.
- מגבלות ה־MVP.

אין להפוך את README למדריך ארוך.

---

# סדר העבודה

## שלב 1

- Architecture
- Config
- Paths
- Main Window בסיסי

## שלב 2

- `FXServerService`
- `DiscordBotService`
- Start / Stop / Restart

## שלב 3

- Status Cards
- Logs
- Safe Shutdown

## שלב 4

- Environment Check
- txAdmin status
- Tailscale status
- Database status

אין לבנות הכול בבת אחת.

בסוף כל שלב:

1. הסבר מה נוצר.
2. הסבר איך לבדוק אותו.
3. ציין אילו קבצים נוצרו או השתנו.
4. המתן לאישור לפני מעבר לשלב הבא.

---

# מגבלות חשובות

- אל תמציא APIs.
- אל תניח ש־MariaDB Portable כבר קיימת.
- אל תשנה Resources של FiveM ללא בקשה מפורשת.
- אל תשנה את מסד הנתונים ללא בקשה מפורשת.
- אל תבצע מחיקות.
- אל תבצע התקנות מערכת אוטומטיות.
- אל תבנה מערכת Plugins בשלב הראשון.
- אל תכתוב את כל האפליקציה בקובץ אחד.
- אל תוסיף מורכבות רק כדי שהמבנה ייראה "מקצועי".
- אין להמשיך לשלב הבא ללא אישור.

---

# המשימה הנוכחית

התחל רק עם:

1. סריקת מבנה הפרויקט.
2. תכנון ארכיטקטורה.
3. רשימת קבצים.
4. זרימת Start / Stop / Restart.
5. בחירה בין `QProcess` ל־`subprocess`.
6. הסבר קצר על הבחירה.
7. המתן לאישור לפני כתיבת קוד.
