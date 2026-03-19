from __future__ import annotations

from app.models import Bundle


# ---------------------------------------------------------------------------
# Bundle catalogue
# ---------------------------------------------------------------------------
# Bundles are grouped into categories that are displayed in the web UI.
# Every bundle maps to a set of Debian apt packages (and optional pip packages)
# that are installed into the image.
#
# Package names target Debian 13 "Trixie" (armhf) — the current official
# BeagleBone Black Debian image base.  A few pip-only packages (e.g. Hugging
# Face Transformers, TFLite) are installed via pip after apt.
# ---------------------------------------------------------------------------

BUNDLES: dict[str, Bundle] = {

    # ── DEVELOPMENT ESSENTIALS ────────────────────────────────────────────

    "core-dev": Bundle(
        name="core-dev",
        description=(
            "The basics every developer needs: git for saving your code, "
            "curl/wget for downloading files, nano/vim text editors, "
            "htop to see what's running, tmux to keep sessions alive, "
            "and a handful of everyday shell utilities."
        ),
        category="Development Essentials",
        apt_packages=[
            "git", "curl", "wget", "nano", "vim", "htop", "tmux", "tree",
            "ca-certificates", "unzip", "zip", "bash-completion", "file",
            "less", "man-db", "rsync", "lsof",
        ],
    ),

    "text-editors": Bundle(
        name="text-editors",
        description=(
            "Extra text editors for the terminal: nano (easiest for beginners), "
            "vim (powerful once you learn it), and micro (modern keyboard shortcuts)."
        ),
        category="Development Essentials",
        apt_packages=["nano", "vim", "micro"],
    ),

    "debugging-tools": Bundle(
        name="debugging-tools",
        description=(
            "Tools to find and fix bugs in C/C++ programs: gdb (step through code "
            "line by line), valgrind (find memory leaks), strace (see every system "
            "call your program makes)."
        ),
        category="Development Essentials",
        apt_packages=["gdb", "valgrind", "strace", "ltrace"],
    ),

    # ── PROGRAMMING LANGUAGES ─────────────────────────────────────────────

    "python": Bundle(
        name="python",
        description=(
            "Python 3 — the most beginner-friendly language for robotics and AI. "
            "Includes pip (package installer) and venv (isolated project environments)."
        ),
        category="Programming Languages",
        apt_packages=[
            "python3", "python3-pip", "python3-venv", "python3-dev",
            "python3-setuptools", "python3-wheel",
        ],
    ),

    "python-science": Bundle(
        name="python-science",
        description=(
            "The scientific Python stack: NumPy (fast arrays), SciPy (maths & signal "
            "processing), Pandas (data tables), Matplotlib (charts), Seaborn (pretty charts). "
            "Essential for data logging and analysis."
        ),
        category="Programming Languages",
        apt_packages=[
            "python3-numpy", "python3-scipy", "python3-pandas",
            "python3-matplotlib", "python3-seaborn",
        ],
    ),

    "python-ml": Bundle(
        name="python-ml",
        description=(
            "Core machine-learning Python libraries: scikit-learn (classic ML algorithms "
            "— decision trees, SVM, k-means clustering), joblib (parallel processing). "
            "Works well on the BBB's ARM processor."
        ),
        category="Programming Languages",
        apt_packages=["python3-sklearn", "python3-joblib"],
    ),

    "cpp": Bundle(
        name="cpp",
        description=(
            "C and C++ development: GCC/G++ compiler, CMake build system, GDB debugger, "
            "pkg-config. The standard toolchain for high-performance embedded code."
        ),
        category="Programming Languages",
        apt_packages=["build-essential", "cmake", "gdb", "pkg-config", "make"],
    ),

    "cpp-advanced": Bundle(
        name="cpp-advanced",
        description=(
            "Advanced C++ tools: Clang compiler (fast, great error messages), LLDB debugger, "
            "Boost libraries (threading, networking, filesystem), ccache (speed up recompilation)."
        ),
        category="Programming Languages",
        apt_packages=["clang", "lldb", "libboost-all-dev", "ccache", "ninja-build"],
    ),

    "rust": Bundle(
        name="rust",
        description=(
            "The Rust programming language — known for memory safety and blazing speed "
            "without a garbage collector. Great for systems programming and robotics firmware."
        ),
        category="Programming Languages",
        apt_packages=["rustc", "cargo"],
    ),

    "nodejs": Bundle(
        name="nodejs",
        description=(
            "Node.js JavaScript runtime and npm package manager. Useful for building "
            "web dashboards, REST APIs, and running JavaScript-based tools."
        ),
        category="Programming Languages",
        apt_packages=["nodejs", "npm"],
    ),

    "java": Bundle(
        name="java",
        description=(
            "Java Development Kit (headless — no GUI). Run and compile Java programs, "
            "useful if your course uses Java or you need Java-based tools."
        ),
        category="Programming Languages",
        apt_packages=["default-jdk-headless"],
    ),

    # ── MACHINE LEARNING & AI ─────────────────────────────────────────────

    "huggingface": Bundle(
        name="huggingface",
        description=(
            "Hugging Face Transformers — run state-of-the-art NLP and vision AI models "
            "(BERT, GPT-2, ViT, etc.) directly on your BBB. Includes the datasets and "
            "tokenizers libraries. Note: large models may be slow on the BBB's ARM CPU."
        ),
        category="Machine Learning & AI",
        apt_packages=["python3-pip", "python3-dev", "python3-numpy"],
        pip_packages=["transformers", "datasets", "tokenizers", "huggingface-hub"],
    ),

    "tflite": Bundle(
        name="tflite",
        description=(
            "TensorFlow Lite — Google's lightweight ML framework optimised for "
            "microcontrollers and single-board computers. Run image classification, "
            "object detection, and pose estimation models with low memory usage."
        ),
        category="Machine Learning & AI",
        apt_packages=["python3-pip", "python3-numpy"],
        pip_packages=["tflite-runtime"],
    ),

    "onnx-runtime": Bundle(
        name="onnx-runtime",
        description=(
            "ONNX Runtime — run models exported from PyTorch, TensorFlow, or scikit-learn "
            "in a fast, cross-platform format. Great for deploying trained models to the BBB."
        ),
        category="Machine Learning & AI",
        apt_packages=["python3-pip", "python3-numpy"],
        pip_packages=["onnxruntime"],
    ),

    "ml-nlp": Bundle(
        name="ml-nlp",
        description=(
            "Natural Language Processing: NLTK (tokenising, stemming, tagging English text), "
            "gensim (Word2Vec, topic modelling). Good for text analysis projects."
        ),
        category="Machine Learning & AI",
        apt_packages=["python3-nltk"],
        pip_packages=["gensim"],
    ),

    # ── COMPUTER VISION ───────────────────────────────────────────────────

    "opencv": Bundle(
        name="opencv",
        description=(
            "OpenCV — the most popular computer vision library. "
            "Detect edges, faces, colours, and objects. Read from USB cameras. "
            "Includes Python bindings, the C++ development headers, and ffmpeg for video."
        ),
        category="Computer Vision",
        apt_packages=[
            "python3-opencv", "libopencv-dev", "v4l-utils", "ffmpeg",
            "libv4l-dev",
        ],
    ),

    "camera-tools": Bundle(
        name="camera-tools",
        description=(
            "Camera capture and streaming tools: fswebcam (grab frames from USB webcams), "
            "GStreamer (stream video over the network or to files). "
            "Use with OpenCV for a full vision pipeline."
        ),
        category="Computer Vision",
        apt_packages=[
            "fswebcam",
            "gstreamer1.0-tools",
            "gstreamer1.0-plugins-base",
            "gstreamer1.0-plugins-good",
            "v4l-utils",
        ],
    ),

    "image-processing": Bundle(
        name="image-processing",
        description=(
            "Image manipulation libraries: Pillow/PIL (Python image library), "
            "ImageMagick (command-line image editing), "
            "scikit-image (scientific image processing algorithms)."
        ),
        category="Computer Vision",
        apt_packages=["python3-pil", "imagemagick", "python3-skimage"],
    ),

    # ── ROBOTICS ──────────────────────────────────────────────────────────

    "robotics-lite": Bundle(
        name="robotics-lite",
        description=(
            "Essential utilities for robotics: serial terminal tools (screen, minicom, picocom) "
            "for talking to Arduino/microcontrollers, usbutils to identify connected USB devices, "
            "and basic networking tools."
        ),
        category="Robotics",
        apt_packages=[
            "screen", "minicom", "picocom", "usbutils", "pciutils", "net-tools",
        ],
    ),

    "robotics-ros": Bundle(
        name="robotics-ros",
        description=(
            "ROS 2 (Robot Operating System 2) — the industry-standard framework for "
            "building robots. Provides topics, services, and a package ecosystem. "
            "IMPORTANT: This bundle uses first-boot mode and requires internet on "
            "the BBB's first startup to download ROS packages (~500 MB)."
        ),
        category="Robotics",
        apt_packages=["python3-pip", "python3-colcon-common-extensions", "locales"],
        pip_packages=["colcon-common-extensions"],
        firstboot_commands=[
            "locale-gen en_US.UTF-8",
            "curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc "
            "| gpg --dearmor -o /usr/share/keyrings/ros-archive-keyring.gpg",
            "echo 'deb [arch=armhf signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] "
            "http://packages.ros.org/ros2/ubuntu jammy main' "
            "> /etc/apt/sources.list.d/ros2.list",
        ],
    ),

    "robotics-sensors": Bundle(
        name="robotics-sensors",
        description=(
            "Python libraries for common robotics sensors: IMU (orientation), GPS (location), "
            "barometer (altitude), and distance sensors from Adafruit and other makers. "
            "Works with the I2C bundles."
        ),
        category="Robotics",
        apt_packages=["python3-smbus", "python3-serial", "python3-pip"],
        pip_packages=[
            "adafruit-blinka",
            "adafruit-circuitpython-bno055",
            "adafruit-circuitpython-gps",
            "adafruit-circuitpython-lsm6ds",
        ],
    ),

    "robotics-motors": Bundle(
        name="robotics-motors",
        description=(
            "Motor and servo control: libraries to drive DC motors, stepper motors, and "
            "servos via PWM controllers (PCA9685 breakout board). "
            "Compatible with most Adafruit motor driver boards."
        ),
        category="Robotics",
        apt_packages=["python3-pip", "python3-smbus"],
        pip_packages=[
            "adafruit-blinka",
            "adafruit-circuitpython-motor",
            "adafruit-circuitpython-pca9685",
            "adafruit-circuitpython-servokit",
        ],
    ),

    # ── HARDWARE INTERFACES ───────────────────────────────────────────────

    "gpio": Bundle(
        name="gpio",
        description=(
            "GPIO (General Purpose Input/Output) — control the BBB's pins directly from Python. "
            "Turn LEDs on and off, read buttons, drive relays. "
            "Includes both the C library (libgpiod) and Python bindings."
        ),
        category="Hardware Interfaces",
        apt_packages=["gpiod", "libgpiod-dev", "python3-libgpiod"],
    ),

    "i2c-spi": Bundle(
        name="i2c-spi",
        description=(
            "I2C and SPI communication protocols — the two most common ways to talk to "
            "sensors, displays, and peripheral chips. Includes i2c-detect to scan for "
            "connected devices, and Python libraries for both protocols."
        ),
        category="Hardware Interfaces",
        apt_packages=["i2c-tools", "python3-smbus", "python3-spidev"],
    ),

    "uart-serial": Bundle(
        name="uart-serial",
        description=(
            "UART/serial communication — talk to Arduino boards, GPS modules, "
            "Bluetooth modules, and other microcontrollers over a serial cable. "
            "Includes picocom terminal and PySerial Python library."
        ),
        category="Hardware Interfaces",
        apt_packages=["picocom", "screen", "setserial", "python3-serial"],
    ),

    "can-bus": Bundle(
        name="can-bus",
        description=(
            "CAN bus networking — used in cars, industrial automation, and advanced robotics "
            "to let multiple microcontrollers talk on one shared wire. "
            "Includes can-utils command-line tools and the python-can library."
        ),
        category="Hardware Interfaces",
        apt_packages=["can-utils"],
        pip_packages=["python-can"],
    ),

    "pwm-servo": Bundle(
        name="pwm-servo",
        description=(
            "PWM (Pulse Width Modulation) for controlling servos, ESCs, and LEDs with "
            "precise timing. Includes Adafruit libraries for PCA9685 16-channel PWM boards — "
            "connect up to 16 servos from a single I2C connection."
        ),
        category="Hardware Interfaces",
        apt_packages=["python3-pip", "python3-smbus"],
        pip_packages=[
            "adafruit-blinka",
            "adafruit-circuitpython-pca9685",
            "adafruit-circuitpython-servokit",
        ],
    ),

    "adc-sensors": Bundle(
        name="adc-sensors",
        description=(
            "Analogue-to-Digital Conversion: read analogue sensors (potentiometers, "
            "light sensors, thermistors) using ADS1x15 ADC boards over I2C. "
            "Also includes lm-sensors for reading onboard temperature sensors."
        ),
        category="Hardware Interfaces",
        apt_packages=["lm-sensors", "python3-pip", "python3-smbus"],
        pip_packages=["adafruit-blinka", "adafruit-circuitpython-ads1x15"],
    ),

    # ── NETWORKING & IOT ──────────────────────────────────────────────────

    "networking": Bundle(
        name="networking",
        description=(
            "Network diagnostic tools: nmap (scan your network for devices), "
            "tcpdump (capture and inspect network traffic), iperf3 (measure network speed), "
            "traceroute (trace the path packets take), and DNS lookup tools."
        ),
        category="Networking & IoT",
        apt_packages=[
            "net-tools", "nmap", "tcpdump", "iperf3", "traceroute",
            "dnsutils", "iproute2", "netcat-openbsd",
        ],
    ),

    "mqtt": Bundle(
        name="mqtt",
        description=(
            "MQTT — the lightweight messaging protocol for IoT. Run a local Mosquitto "
            "broker on your BBB to receive sensor data, or publish readings to cloud "
            "services like Home Assistant, AWS IoT, or Node-RED."
        ),
        category="Networking & IoT",
        apt_packages=["mosquitto", "mosquitto-clients", "python3-paho-mqtt"],
        services=["mosquitto"],
    ),

    "bluetooth": Bundle(
        name="bluetooth",
        description=(
            "Bluetooth tools: scan for nearby devices, pair with sensors and phones, "
            "send and receive data over BLE or classic Bluetooth. "
            "Includes BlueZ daemon and Python-DBus bindings."
        ),
        category="Networking & IoT",
        apt_packages=["bluez", "bluetooth", "python3-dbus"],
        services=["bluetooth"],
    ),

    "wifi-tools": Bundle(
        name="wifi-tools",
        description=(
            "WiFi scanning and configuration tools: scan for available networks, "
            "check signal strength, and configure WPA/WPA2 connections manually. "
            "Includes iw, wireless-tools, and wpa_supplicant."
        ),
        category="Networking & IoT",
        apt_packages=["wireless-tools", "iw", "wpasupplicant"],
    ),

    "http-tools": Bundle(
        name="http-tools",
        description=(
            "HTTP and API tools: curl and wget (download files, test REST APIs), "
            "jq (parse and pretty-print JSON responses), "
            "httpie (human-friendly HTTP client for testing APIs)."
        ),
        category="Networking & IoT",
        apt_packages=["curl", "wget", "jq"],
        pip_packages=["httpie"],
    ),

    "nodered": Bundle(
        name="nodered",
        description=(
            "Node-RED — a visual, drag-and-drop programming tool for wiring together "
            "sensors, APIs, and dashboards without writing much code. "
            "Very popular for IoT projects and home automation."
        ),
        category="Networking & IoT",
        apt_packages=["nodejs", "npm"],
        pip_packages=[],
        firstboot_commands=["npm install -g --unsafe-perm node-red"],
    ),

    # ── DATA & STORAGE ────────────────────────────────────────────────────

    "sqlite": Bundle(
        name="sqlite",
        description=(
            "SQLite — a simple, file-based database. No server needed. "
            "Perfect for logging sensor data, storing robot states, or building "
            "small data-driven applications. Includes the CLI and Python bindings."
        ),
        category="Data & Storage",
        apt_packages=["sqlite3", "libsqlite3-dev"],
    ),

    "databases": Bundle(
        name="databases",
        description=(
            "Database client tools: connect to MariaDB/MySQL and Redis servers "
            "from your BBB. Useful when your BBB is part of a larger system that "
            "uses a central database server."
        ),
        category="Data & Storage",
        apt_packages=["mariadb-client", "redis-tools"],
        pip_packages=["pymysql", "redis"],
    ),

    # ── SYSTEM & MONITORING ───────────────────────────────────────────────

    "monitoring": Bundle(
        name="monitoring",
        description=(
            "System monitoring tools: iotop (see which process is hammering the SD card), "
            "sysstat (collect CPU/memory/disk statistics over time), "
            "nethogs (see which process is using the network), dstat (live system stats)."
        ),
        category="System & Monitoring",
        apt_packages=["iotop", "sysstat", "nethogs", "dstat", "procps"],
    ),

    "security-tools": Bundle(
        name="security-tools",
        description=(
            "Basic security hardening: fail2ban (automatically block IPs that keep "
            "failing SSH login attempts), UFW (simple firewall — block ports you don't need). "
            "Recommended for any BBB exposed to the internet."
        ),
        category="System & Monitoring",
        apt_packages=["fail2ban", "ufw"],
        services=["fail2ban"],
    ),

    "system-utils": Bundle(
        name="system-utils",
        description=(
            "Handy system utilities: lsblk (list storage devices), parted (manage "
            "disk partitions), pv (progress bar for file copies), bc (command-line "
            "calculator), and other quality-of-life tools."
        ),
        category="System & Monitoring",
        apt_packages=["parted", "pv", "bc", "at", "cron", "logrotate"],
    ),
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def bundle_names() -> list[str]:
    return sorted(BUNDLES)


def bundles_by_category() -> dict[str, list[Bundle]]:
    """Return bundles grouped by their category, with categories sorted."""
    result: dict[str, list[Bundle]] = {}
    for bundle in BUNDLES.values():
        result.setdefault(bundle.category, []).append(bundle)
    return dict(sorted(result.items()))


def resolve_packages(bundle_list: list[str], extra_packages: list[str] | None = None) -> list[str]:
    packages: set[str] = set()
    for bundle_name in bundle_list:
        bundle = BUNDLES.get(bundle_name)
        if bundle is None:
            raise KeyError(f"Unknown bundle: {bundle_name!r}")
        packages.update(bundle.apt_packages)
    if extra_packages:
        packages.update(extra_packages)
    return sorted(packages)


def resolve_pip_packages(bundle_list: list[str]) -> list[str]:
    packages: set[str] = set()
    for bundle_name in bundle_list:
        bundle = BUNDLES.get(bundle_name)
        if bundle is None:
            raise KeyError(f"Unknown bundle: {bundle_name!r}")
        packages.update(bundle.pip_packages)
    return sorted(packages)


def resolve_firstboot_commands(bundle_list: list[str]) -> list[str]:
    """Return firstboot_commands from all selected bundles, in order, deduplicated."""
    seen: set[str] = set()
    result: list[str] = []
    for bundle_name in bundle_list:
        bundle = BUNDLES.get(bundle_name)
        if bundle is None:
            continue
        for cmd in bundle.firstboot_commands:
            if cmd not in seen:
                seen.add(cmd)
                result.append(cmd)
    return result
