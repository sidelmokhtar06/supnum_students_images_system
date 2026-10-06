# SupNum – Photos des nouveaux étudiants

Students enter their matricule (must start with `26`) and take or upload a photo.
Each photo is converted to JPEG and saved as `uploads/<MATRICULE>.jpg`. A matricule can only be used once.
Admin page: `/admin` (view, rename, delete, download one or all as a zip).

---

## Run it (the short version)

```bash
cd ~/Projects/supnum_students_images
ADMIN_PASSWORD='choose-a-strong-password' ./run.sh
```

It prints the link to give students (and a QR code if `qrencode` is installed). Leave the terminal open. **Ctrl+C** stops it.
Photos stay in `uploads/` between runs.

### One-time setup (optional but recommended)

```bash
sudo pacman -S qrencode cloudflared   # QR code in the terminal + public-link fallback
```

---

## On the day: checklist

1. **Connect the laptop to the same Wi-Fi as the students.**
2. **Start it:** `ADMIN_PASSWORD='...' ./run.sh`
3. **Test from your phone** on that Wi-Fi: open the printed link. If it loads → share it (QR code on the projector is easiest).
4. **Keep the laptop plugged in and awake**: disable sleep / screen lock for the session.
5. Check `/admin` from time to time to see photos arriving.
6. **At the end:** download everything from `/admin` (*Tout télécharger*) **and** copy the `uploads/` folder somewhere safe (USB, Drive).

> The IP address can change between days or networks, so always use the link `run.sh` prints, not an old one.

---

## If the link doesn't work for students

**Plan A – Public link with Cloudflare Tunnel** (best fallback, needs internet on the laptop)

```bash
ADMIN_PASSWORD='...' ./run.sh --tunnel
```

It prints a second link like `https://something-random.trycloudflare.com`. It works on any network (school Wi-Fi, 4G…),
uses HTTPS, and needs no account. The link changes every time you restart, so share the new one.

**Plan B – Laptop hotspot** (no internet needed)

Turn the laptop into a Wi-Fi network and have students join it:

```bash
nmcli device wifi hotspot ssid SupNum-Photos password supnum2026
ADMIN_PASSWORD='...' ./run.sh          # the printed link will be http://10.42.0.1:5000
```

The laptop leaves the school Wi-Fi while the hotspot is on. Most laptop Wi-Fi cards handle only ~10–20 phones at once,
so let students come in groups. Stop the hotspot with `nmcli connection down Hotspot`.

**Plan C – Phone hotspot**: turn on your phone's hotspot, connect the laptop **and** the students to it, run `./run.sh`
and share the link it prints. Fine for small groups; uses your mobile data only if students browse elsewhere.

### Troubleshooting

| Problem | Fix |
| --- | --- |
| Page loads on the laptop but not on phones | The Wi-Fi blocks device-to-device traffic → use Plan A or B |
| `Address already in use` | Another copy is running. Close it, or use another port: `PORT=5050 ./run.sh` |
| `ADMIN_PASSWORD: Set it first` | You forgot the password part of the command |
| Tunnel failed | Check the laptop has internet; details in `.tunnel.log` |

---

## Deploy online (PythonAnywhere)

Files there live on a normal disk, so photos survive restarts and code updates.

1. Create a free account on pythonanywhere.com. The site will be `https://USERNAME.pythonanywhere.com`.
2. **Consoles → Bash**:
   ```bash
   git clone https://github.com/GITHUB_USER/supnum_students_images.git supnum
   cd ~/supnum && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
   ```
3. **Web → Add a new web app → Manual configuration → Python 3.12**, then set
   Source code `/home/USERNAME/supnum`, Virtualenv `/home/USERNAME/supnum/.venv`, and turn on **Force HTTPS**.
4. Open the **WSGI configuration file** from the Web tab, replace its content with:
   ```python
   import os, sys
   os.environ["SECRET_KEY"] = "a-long-random-string"
   os.environ["ADMIN_PASSWORD"] = "your-strong-password"
   sys.path.insert(0, "/home/USERNAME/supnum")
   from app import app as application
   ```
5. Click **Reload**.

**Updating later:** `cd ~/supnum && git pull`, then **Reload**. Photos in `uploads/` are not in git, so they are never touched.
**Backups:** download the zip from `/admin` regularly. Never delete the `~/supnum` folder on the server.

---

## Development

```bash
SECRET_KEY=dev ADMIN_PASSWORD=admin .venv/bin/flask run --debug   # auto-reload, local only
```

Never use `--debug` when students are connected: the debugger can be reached over the network.
