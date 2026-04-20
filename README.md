# BBB Image Forge

**Build a custom BeagleBone Black image — no experience needed.**

---

## What is a BeagleBone Black?

A BeagleBone Black (BBB) is a small, credit-card-sized computer that runs Linux.
It is designed for engineering, robotics, and electronics projects.

Unlike a regular computer, it has a row of **pins** on both sides that you can connect to LEDs, motors, sensors, cameras, and other electronics. You write code on it just like a normal Linux computer — in Python, C++, or whatever language you like — and that code can control physical things in the real world.

Think of it as a tiny, hackable Linux computer that you can wire up to a robot.

---

## What does this tool do?

Setting up a BeagleBone Black from scratch normally takes hours of typing commands, fixing errors, and troubleshooting — not great if you have never used Linux before.

**BBB Image Forge** skips all of that.

You fill in a web form, pick the software you want, and it builds a ready-to-use image file. You flash that image to a microSD card, plug it into your BBB, and it just works — with your chosen software, your username, your password, and your network settings already configured.

---

## What you need before you start

| Item | Where to get it | Notes |
|------|----------------|-------|
| A BeagleBone Black | Online (Amazon, Mouser, DigiKey) | The original BBB or BBB Industrial |
| A microSD card | Online or any electronics shop | **8 GB minimum**, Class 10 or faster |
| A microSD card reader | Most laptops have one built in | Or buy a USB card reader for ~£5 |
| An Ethernet cable | Any spare cable from home | Connects your BBB to your router |
| A Linux computer | Your own, or a lab machine | Needed to build the image |
| Python 3.11 or newer | python.org | Usually already installed on Linux |

> **On Windows or macOS?** You can still build images — use [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install) (Windows Subsystem for Linux) on Windows, or a Linux VM. The web UI works on any OS; the actual image build must run on Linux.

---

## Step 1 — Install the required system tools (Linux)

Open a terminal. If you do not know what a terminal is: press `Ctrl + Alt + T` on most Linux desktops, or search for "Terminal" in your applications menu.

Paste this command and press Enter:

```bash
sudo apt-get update && sudo apt-get install -y \
  git python3 python3-pip python3-venv \
  qemu-user-static xz-utils parted \
  util-linux mount rsync
```

> **What is `sudo`?** It means "run this as administrator." Your computer may ask for your password. Type it and press Enter (the cursor will not move while you type — that is normal).

---

## Step 2 — Download this tool

In the terminal, type:

```bash
git clone https://github.com/Eliot-Abramo/BBB-Image-Flasher.git
cd BBB-Image-Flasher
```

> **What is `git clone`?** It downloads a copy of this project to your computer. The second command moves you into the downloaded folder.

---

## Step 3 — Set up the Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> **What is a virtual environment?** It is a self-contained box for Python that keeps this project's libraries separate from everything else on your computer. You will see `(.venv)` at the start of your terminal prompt after running `source .venv/bin/activate` — that means it is active. You need to run that activation command every time you open a new terminal.

---

## Step 4 — Start the web interface

```bash
python -m app.main
```

Now open your web browser and go to:

```
http://127.0.0.1:8000
```

You will see the BBB Image Forge web interface. Keep the terminal open — it must stay running while you use the tool.

---

## Step 5 — Build your image using the web interface

The web form has five sections. Work through them from top to bottom.

### Section 1 — Choose a Starting Point

Pick a pre-made profile that matches your project. Here is what each one includes:

| Profile | Best for | What's included |
|---------|----------|----------------|
| **Beginner Starter** | First-timers | Python 3, git, nano, htop, curl, serial tools |
| **Python Lab** | Python + sensors | Python + NumPy/Pandas/Matplotlib + GPIO + I2C/SPI |
| **Robotics Starter** | First robot | Python + C++ + GPIO + I2C + UART + PWM servo + motor libs |
| **Robotics + ROS 2** | Serious robotics | Everything in Robotics Starter + ROS 2 (needs internet on first boot) |
| **Computer Vision** | Camera projects | OpenCV + GStreamer + Pillow + scikit-image + ffmpeg |
| **ML / AI Starter** | Edge AI | scikit-learn + TFLite + ONNX Runtime + OpenCV |
| **Hugging Face AI** | NLP / language models | Transformers + Datasets + Tokenizers + NLTK |
| **IoT & Sensors** | Smart home / data logging | MQTT + sensor libs + SQLite + networking tools |
| **Embedded Systems** | Low-level C/C++ | GCC + Clang + Boost + full hardware interfaces + CAN bus |
| **Full Robotics Stack** | Advanced projects | All of the above (large image, ~2 GB) |

**Not sure?** Choose **Robotics Starter** — it covers most first-year engineering projects.

### Section 2 — Set Up Your BBB

- **Hostname**: A name for your BBB on the network. Use something like `bbb-robot`. No spaces, no special characters.
- **Username**: The account you will log into. `student` is a good default.
- **Password**: What you type to SSH in. The default is `beaglebone`. Change it to something you will remember.

### Section 3 — Network Settings

- **Automatic (DHCP)** — Recommended. Your router assigns an IP address automatically. You look up what address it got from your router's admin page or with `nmap`.
- **Static IP** — Choose this if you want your BBB to always have the same address. You will need to know your network's address range (e.g. `192.168.1.x`) and your router's IP (the gateway).

### Section 4 — Add Extra Software

These are optional extras on top of your chosen profile. Each one shows a description so you can see exactly what it installs. Only tick what you know you need — more packages means a longer build.

Here is a summary of all available packages:

#### Development Essentials
| Package | What it does |
|---------|-------------|
| `core-dev` | git, curl, nano, vim, htop, tmux, tree, bash-completion |
| `text-editors` | nano, vim, micro (all text editors) |
| `debugging-tools` | gdb, valgrind, strace (find and fix bugs) |

#### Programming Languages
| Package | What it does |
|---------|-------------|
| `python` | Python 3, pip, venv |
| `python-science` | NumPy, SciPy, Pandas, Matplotlib, Seaborn |
| `python-ml` | scikit-learn, joblib |
| `cpp` | GCC/G++, CMake, gdb, pkg-config |
| `cpp-advanced` | Clang, LLDB, Boost libraries, ccache |
| `rust` | Rust compiler and Cargo package manager |
| `nodejs` | Node.js and npm |
| `java` | Java Development Kit (JDK, headless) |

#### Machine Learning & AI
| Package | What it does |
|---------|-------------|
| `huggingface` | Transformers, Datasets, Tokenizers (pip install) |
| `tflite` | TensorFlow Lite for ARM (pip install) |
| `onnx-runtime` | ONNX Runtime for deploying PyTorch/TF models (pip) |
| `ml-nlp` | NLTK, gensim (natural language processing) |

#### Computer Vision
| Package | What it does |
|---------|-------------|
| `opencv` | OpenCV 4 — Python + C++ bindings, ffmpeg, v4l2 |
| `camera-tools` | fswebcam, GStreamer (capture and stream video) |
| `image-processing` | Pillow (PIL), ImageMagick, scikit-image |

#### Robotics
| Package | What it does |
|---------|-------------|
| `robotics-lite` | screen, minicom, picocom, usbutils, net-tools |
| `robotics-ros` | ROS 2 apt repo setup (firstboot mode only, needs internet) |
| `robotics-sensors` | Adafruit libs for IMU, GPS, distance sensors |
| `robotics-motors` | Adafruit libs for DC motors, steppers, servos (PCA9685) |

#### Hardware Interfaces
| Package | What it does |
|---------|-------------|
| `gpio` | gpiod, libgpiod, Python bindings — control BBB pins |
| `i2c-spi` | i2c-tools, python3-smbus, spidev — talk to chips |
| `uart-serial` | picocom, screen, PySerial — serial/UART comm |
| `can-bus` | can-utils, python-can — CAN bus for automotive/robotics |
| `pwm-servo` | Adafruit PCA9685 libs — control up to 16 servos |
| `adc-sensors` | ADS1x15 ADC libs — read analogue sensors |

#### Networking & IoT
| Package | What it does |
|---------|-------------|
| `networking` | nmap, tcpdump, iperf3, traceroute, dnsutils |
| `mqtt` | Mosquitto broker + paho-mqtt Python client |
| `bluetooth` | BlueZ daemon, Python-DBus bindings |
| `wifi-tools` | iw, wireless-tools, wpa_supplicant |
| `http-tools` | curl, wget, jq, httpie |
| `nodered` | Node-RED visual IoT programming (firstboot install) |

#### Data & Storage
| Package | What it does |
|---------|-------------|
| `sqlite` | SQLite database — log sensor data locally |
| `databases` | MariaDB and Redis client tools |

#### System & Monitoring
| Package | What it does |
|---------|-------------|
| `monitoring` | iotop, sysstat, nethogs, dstat |
| `security-tools` | fail2ban (block brute-force SSH), UFW firewall |
| `system-utils` | parted, pv, bc, cron, logrotate |

### Section 5 — SSH Access Settings

SSH is how you connect to your BBB remotely from your laptop's terminal.

- **Leave "Disable password login" unchecked** — password login is the easiest option for beginners.
- **Leave "Allow root SSH login" unchecked** — log in as your user and use `sudo` when you need admin rights.
- **SSH Public Key** — leave blank for now. You can always add one later once you are comfortable.

### Click Generate

When you click **Generate My Manifest**, you will see a JSON configuration file. This is your **manifest** — the recipe for your image.

Save it by:

1. Selecting all the text (Ctrl+A)
2. Copying it (Ctrl+C)
3. Opening a text editor and pasting it
4. Saving it as `my-bbb.json`

Or use your browser's "Save Page As" option.

---

## Step 6 — Build the image

Go back to your terminal (make sure `.venv` is still active — you should see `(.venv)` at the start of the line).

Run:

```bash
sudo python -m app.cli build my-bbb.json
```

> **Why `sudo`?** The build process needs administrator rights to mount the disk image (like attaching a virtual hard drive) so it can install software into it.

The build process will:

1. Download the official BeagleBone Black Debian image (~1 GB — takes a few minutes)
2. Verify the download is not corrupted
3. Mount the image and install all your chosen packages (10–30 minutes depending on how many you chose)
4. Apply your settings (hostname, username, password, network)
5. Compress the finished image

When it finishes, you will find your image in the `build/artifacts/` folder. It will be named something like `bbb-robot.img.xz`.

---

## Step 7 — Flash the image to your microSD card

You need a tool called **balenaEtcher** — it is free and works on Windows, Mac, and Linux.

1. Download it from **[balena.io/etcher](https://www.balena.io/etcher/)**
2. Insert your microSD card into your computer
3. Open balenaEtcher
4. Click **Flash from file** and select your `bbb-robot.img.xz` file
5. Click **Select target** and choose your microSD card
6. Click **Flash!** and wait for it to finish (3–5 minutes)

> **Warning:** Make sure you select the right drive. Etcher will erase everything on whatever you pick. Do not accidentally select your main hard drive!

---

## Step 8 — Boot your BBB

1. Insert the flashed microSD card into the BBB (the slot is on the underside)
2. Connect an Ethernet cable between your BBB and your router
3. Power on the BBB (connect a 5V USB cable — the BBB uses the same connector as many Android phones, or a dedicated barrel jack)
4. Wait 30–60 seconds. The blue LEDs on the BBB will blink while it boots.

> **Tip:** The first boot may take a little longer because it resizes the file system and applies final setup.

---

## Step 9 — Connect to your BBB via SSH

SSH (Secure Shell) is how you type commands on your BBB from your laptop.

### Find your BBB's IP address

Your BBB got an IP address from your router automatically. To find it:

**Option A — Check your router's admin page**
- Open a browser and go to `192.168.1.1` (or `192.168.0.1` — try both)
- Log in with your router's admin password (often on a sticker on the router)
- Look for a list of connected devices — your BBB will appear as `bbb-robot` (or whatever hostname you chose)

**Option B — Scan the network**
```bash
nmap -sn 192.168.1.0/24
```
Change `192.168.1` to match your network. Look for a device named after your hostname.

**Option C — Try the hostname directly**
```bash
ssh student@bbb-robot.local
```
This works on most home networks without needing to know the IP address.

### SSH in

Once you have the IP address, open a terminal and type:

```bash
ssh student@192.168.1.100
```

Replace `192.168.1.100` with your BBB's actual IP address, and `student` with your chosen username.

When it asks for a password, type the password you set in the web form (default: `beaglebone`).

**You're in!** You should see a command prompt that looks like:

```
student@bbb-robot:~$
```

You are now controlling your BeagleBone Black.

### SSH on Windows

Download and install **PuTTY** from [putty.org](https://www.putty.org/).

- Host Name: `192.168.1.100` (your BBB's IP)
- Port: `22`
- Connection type: SSH
- Click Open, log in with your username and password

---

## What to do once you are connected

Here are some useful first commands:

```bash
# Check Python is installed
python3 --version

# Install a Python package (example: adafruit-blinka for hardware access)
pip3 install adafruit-blinka --break-system-packages

# Check which packages are installed
dpkg -l | grep python3

# Check disk space
df -h

# Check memory usage
free -h

# List the BBB's hardware pins (if bone-pinmux-helper is installed)
ls /sys/class/gpio/

# Run a Python script
python3 my_script.py

# Reboot the BBB
sudo reboot

# Shut down safely
sudo poweroff
```

---

## Troubleshooting

### "I cannot connect via SSH"

- Make sure the Ethernet cable is connected to your router (not directly to your laptop — use a router in between)
- Check the BBB's blue LEDs are solid or slowly blinking (not all off) — it needs to have finished booting
- Try waiting another 30 seconds and try again
- Check your router's admin page for the correct IP address
- Make sure you are typing the right username and password

### "Permission denied" when SSH-ing

- Double-check your password. The default is `beaglebone`
- If you set "disable password login" and did not paste an SSH key, you are locked out — you will need to rebuild the image

### "The build failed"

- Make sure you ran the build with `sudo`
- Make sure `qemu-user-static` is installed: `sudo apt-get install qemu-user-static`
- Check you have enough disk space: `df -h` (you need at least 10 GB free)

### "The image is too big for my SD card"

- Use an 8 GB or larger microSD card
- Consider choosing fewer packages and rebuilding

### "I picked Robotics + ROS 2 but ROS did not install"

- The ROS profile uses "firstboot" mode — ROS installs on the BBB itself during the first boot
- Make sure your BBB has internet access on first boot (Ethernet connected to a router with internet)
- The first boot will take 10–20 minutes while it downloads ROS — do not power off!
- Check progress: `journalctl -f -u bbb-image-forge-firstboot.service`

---

## Frequently asked questions

**Do I need to buy anything extra?**
Just a microSD card (8 GB+) and a microSD card reader if your laptop does not have one. Everything else you likely already have.

**Can I use WiFi instead of Ethernet?**
Yes — go back to the web UI, set your WiFi SSID and password in the Network section, rebuild the image. Note: the BBB does not have built-in WiFi; you need a USB WiFi dongle.

**Can I run this on Windows?**
The web interface works on any OS. The image build (the part that installs packages) requires Linux. On Windows, install [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install), then follow the Linux instructions inside WSL.

**What if I want different software after flashing?**
You can install packages directly on the BBB once connected: `sudo apt-get install package-name`. Or rebuild the image with different options.

**Can I write my Python scripts on my laptop and run them on the BBB?**
Yes! Use `scp` to copy files:
```bash
scp my_script.py student@192.168.1.100:~/
```
Or use VS Code with the Remote-SSH extension to edit files on the BBB directly from your laptop.

**What is the BBB's default login if I do not change anything?**
Username: `student`, Password: `beaglebone`, Hostname: `bbb-robot` (for the Robotics Starter profile).

---

## Project structure

```
BBB-Image-Flasher/
├── app/
│   ├── main.py           Web UI server (FastAPI)
│   ├── cli.py            Command-line interface
│   ├── models.py         Data models (manifest schema)
│   ├── bundles.py        All software bundle definitions (~30 bundles)
│   ├── profiles.py       Profile loading logic
│   ├── manifests.py      Manifest load/save
│   ├── catalog.py        Fetches official BBB images from beagleboard.org
│   ├── builder.py        Core image build engine (download, mount, chroot, install)
│   ├── templates/
│   │   └── index.html    The web form
│   └── profiles/         Pre-made profile YAML files
│       ├── beginner_starter.yml
│       ├── python_lab.yml
│       ├── robotics_starter.yml
│       ├── robotics_ros.yml
│       ├── cv_opencv.yml
│       ├── ml_ai.yml
│       ├── huggingface_ai.yml
│       ├── iot_sensors.yml
│       ├── embedded_systems.yml
│       └── full_robotics_stack.yml
├── scripts/
│   └── run_dev.sh        Quick dev server launcher
├── tests/
│   └── test_bundles.py   Unit tests
├── requirements.txt
└── pyproject.toml
```

---

## CLI reference

If you prefer the command line over the web interface:

```bash
# List available profiles
python -m app.cli list-profiles

# List official base images from beagleboard.org
python -m app.cli list-base-images

# Generate a manifest from a profile
python -m app.cli generate-manifest \
  --profile robotics_starter \
  --hostname bbb-robot \
  --username student \
  --output my-bbb.json

# Build an image from a manifest (requires sudo)
sudo python -m app.cli build my-bbb.json

# Validate a manifest file
python -m app.cli validate my-bbb.json
```

---

## How the image build works (for the curious)

1. **Download** the official BeagleBone Black Debian image from `beagleboard.org`
2. **Verify** the SHA-256 checksum to make sure the download is not corrupted
3. **Decompress** the `.img.xz` file to a raw `.img` disk image
4. **Mount** the disk image as a loop device (like plugging in a virtual USB drive)
5. **Chroot** into the ARM filesystem using `qemu-user-static` — this lets your x86 Linux machine run ARM Linux programs
6. **Configure** hostname, user account, password, SSH settings, and network
7. **Install** all chosen apt packages (and pip packages where needed)
8. **Unmount** everything cleanly
9. **Compress** back to `.img.xz` ready for flashing

The whole process runs offline on your computer — the BBB's first boot is instant, with everything already installed.

---

## Safety notes

- The build process requires `sudo` because it mounts disk images. Do not run untrusted manifests.
- Password set in the manifest is stored in plaintext in the JSON file. Do not commit manifest files with real passwords to public git repositories.
- The default password `beaglebone` is publicly known — change it as soon as you can.

---

## Contributing

Pull requests welcome. Please keep the beginner-friendly approach in mind — every feature should be usable by someone who has never opened a terminal before.

---

*Built with FastAPI, Pydantic, and a lot of patience.*
