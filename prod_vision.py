import asyncio
import cv2
import numpy as np
from playwright.async_api import async_playwright
import os
import random
import shutil
from datetime import datetime
import sys # Biblioteca para detectar se é Windows ou Linux
from urllib.parse import urlparse, unquote

# ==========================================
# CONFIGURAÇÕES DE GRAVAÇÃO / PRODUÇÃO
# ==========================================
MAX_CONCURRENT_BROWSERS = 1  # Modo teste: 1 navegador por vez
MAX_PROXY_RETRIES_PER_PHONE = 3
HEADLESS_MODE = False        # Falso para abrir a tela e gravar
TARGET_URL = "https://okslots4.com/"
INITIAL_PAGE_STABILIZATION_MS = 3500
PAGE_READY_TIMEOUT_MS = 20000
NETWORK_IDLE_TIMEOUT_MS = 9000
INITIAL_GATE_TIMEOUT_MS = 14000
LOGOUT_POPUP_WAIT_MS = 1200
LOGOUT_SEARCH_TIMEOUT_MS = 9000
LOGOUT_CONFIRM_POPUP_WAIT_MS = 1200
LOGOUT_CONFIRM_SEARCH_TIMEOUT_MS = 9000
REGISTER_ENTRY_POPUP_WAIT_MS = 1800
REGISTER_ENTRY_SEARCH_TIMEOUT_MS = 9000
REGISTER_FORM_POPUP_WAIT_MS = 1200
REGISTER_FORM_READY_TIMEOUT_MS = 9000
PHONE_INPUT_SEARCH_TIMEOUT_MS = 9000
PASS_INPUT_SEARCH_TIMEOUT_MS = 9000
PASS_CONFIRM_INPUT_SEARCH_TIMEOUT_MS = 9000
FINAL_REGISTER_BUTTON_SEARCH_TIMEOUT_MS = 9000
FLOW_MODE = "gear_logout_confirm_register_form_only"  # valida OK1010/engrenagem + sair + confirmar + inscrever + phone/pass/pass_confirm + botao final amarelo
REGISTER_PASSWORD = "SenhaPadrao123!"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
PROXIES_FILE = os.path.join(BASE_DIR, "proxies.txt")
SUCCESS_FILE = os.path.join(BASE_DIR, "sucessos_okslots.txt")
VIDEO_RECORDING_ENABLED = False
VIDEO_OUTPUT_DIR = os.path.join(BASE_DIR, "analise", "videos")
VIDEO_RECORDING_SIZE = {"width": 1280, "height": 720}

DEFAULT_TEMPLATE_THRESHOLD = 0.70
TEMPLATE_MATCH_SCALES = (0.90, 0.95, 1.00, 1.05, 1.10)
TEMPLATE_THRESHOLDS = {
    "tpl_btn_ok_1010.png": 0.68,
    "tpl_btn_engrenagem.png": 0.56,
    "tpl_btn_sair.png": 0.62,
    "tpl_btn_confirmar.png": 0.56,
    "tpl_btn_inscrever.png": 0.85,
    "tpl_btn_fechar_bonus.png": 0.56,
    "tpl_btn_sair_config.png": 0.62,
    "tpl_btn_confirmar_sair.png": 0.56,
    "tpl_input_phone.png": 0.62,
    "tpl_input_pass.png": 0.62,
    "tpl_input_pass_confirm.png": 0.62,
    "tpl_btn_inscrever_amarelo.png": 0.56,
    "tpl_btn_deposito.png": 0.56,
}
REQUIRED_TEMPLATES_FULL = (
    "tpl_btn_ok_1010.png",
    "tpl_btn_engrenagem.png",
    "tpl_btn_sair.png",
    "tpl_btn_confirmar.png",
    "tpl_btn_inscrever.png",
    "tpl_input_phone.png",
    "tpl_input_pass.png",
    "tpl_input_pass_confirm.png",
    "tpl_btn_inscrever_amarelo.png",
)
REQUIRED_TEMPLATES_GEAR_ONLY = ("tpl_btn_engrenagem.png",)
REQUIRED_TEMPLATES_INITIAL_GATE_ONLY = ("tpl_btn_ok_1010.png", "tpl_btn_engrenagem.png")
REQUIRED_TEMPLATES_GEAR_LOGOUT_ONLY = ("tpl_btn_ok_1010.png", "tpl_btn_engrenagem.png", "tpl_btn_sair.png")
REQUIRED_TEMPLATES_GEAR_LOGOUT_CONFIRM_ONLY = (
    "tpl_btn_ok_1010.png",
    "tpl_btn_engrenagem.png",
    "tpl_btn_sair.png",
    "tpl_btn_confirmar.png",
)
REQUIRED_TEMPLATES_GEAR_LOGOUT_CONFIRM_REGISTER_ONLY = (
    "tpl_btn_ok_1010.png",
    "tpl_btn_engrenagem.png",
    "tpl_btn_sair.png",
    "tpl_btn_confirmar.png",
    "tpl_btn_inscrever.png",
)
REQUIRED_TEMPLATES_GEAR_LOGOUT_CONFIRM_REGISTER_INPUTS_ONLY = (
    "tpl_btn_ok_1010.png",
    "tpl_btn_engrenagem.png",
    "tpl_btn_sair.png",
    "tpl_btn_confirmar.png",
    "tpl_btn_inscrever.png",
    "tpl_input_phone.png",
    "tpl_input_pass.png",
    "tpl_input_pass_confirm.png",
)
REQUIRED_TEMPLATES_GEAR_LOGOUT_CONFIRM_REGISTER_FORM_ONLY = (
    "tpl_btn_ok_1010.png",
    "tpl_btn_engrenagem.png",
    "tpl_btn_sair.png",
    "tpl_btn_confirmar.png",
    "tpl_btn_inscrever.png",
    "tpl_input_phone.png",
    "tpl_input_pass.png",
    "tpl_input_pass_confirm.png",
    "tpl_btn_inscrever_amarelo.png",
)
OPTIONAL_TEMPLATES = ()
TEMPLATE_VARIANTS_CACHE = {}


def get_required_templates():
    if FLOW_MODE == "gear_logout_confirm_register_inputs_only":
        return REQUIRED_TEMPLATES_GEAR_LOGOUT_CONFIRM_REGISTER_INPUTS_ONLY
    if FLOW_MODE == "gear_logout_confirm_register_form_only":
        return REQUIRED_TEMPLATES_GEAR_LOGOUT_CONFIRM_REGISTER_FORM_ONLY
    if FLOW_MODE == "gear_logout_confirm_register_only":
        return REQUIRED_TEMPLATES_GEAR_LOGOUT_CONFIRM_REGISTER_ONLY
    if FLOW_MODE == "gear_logout_confirm_only":
        return REQUIRED_TEMPLATES_GEAR_LOGOUT_CONFIRM_ONLY
    if FLOW_MODE == "gear_logout_only":
        return REQUIRED_TEMPLATES_GEAR_LOGOUT_ONLY
    if FLOW_MODE == "initial_gate_only":
        return REQUIRED_TEMPLATES_INITIAL_GATE_ONLY
    if FLOW_MODE == "gear_only":
        return REQUIRED_TEMPLATES_GEAR_ONLY
    return REQUIRED_TEMPLATES_FULL

ANSI_COLORS = {
    "INFO": "\033[96m",
    "SUCCESS": "\033[92m",
    "WARN": "\033[93m",
    "ERROR": "\033[91m",
}
ANSI_RESET = "\033[0m"


def log(phone, message, level="INFO"):
    normalized_level = level.upper()
    # Verbosity gate: suppress INFO and SUCCESS to reduce terminal noise
    if normalized_level in ("INFO", "SUCCESS"):
        return

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    context_phone = phone if phone else "SYSTEM"
    color = ANSI_COLORS.get(normalized_level, ANSI_COLORS["INFO"])
    print(f"{color}[{timestamp}] [{context_phone}] [{normalized_level}] {message}{ANSI_RESET}")


def detect_system_browser_path():
    linux_candidates = [
        "chromium",
        "chromium-browser",
        "google-chrome-stable",
        "google-chrome",
        "/snap/bin/chromium",
    ]
    windows_candidates = [
        r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        r"C:\\Program Files\\Chromium\\Application\\chrome.exe",
        r"C:\\Program Files (x86)\\Chromium\\Application\\chrome.exe",
        r"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
        r"C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    ]

    candidates = linux_candidates if sys.platform.startswith("linux") else windows_candidates
    for candidate in candidates:
        resolved = shutil.which(candidate) if not os.path.isabs(candidate) else candidate
        if resolved and os.path.exists(resolved):
            return resolved

    return None


async def launch_browser_multi_os(playwright_obj):
    base_args = {"headless": HEADLESS_MODE}
    launch_attempts = []

    system_browser = detect_system_browser_path()

    if sys.platform.startswith("linux"):
        log("SYSTEM", "Linux detected. Preparing launch strategies.", "INFO")
        if system_browser:
            launch_attempts.append(
                (
                    "system_chromium",
                    {
                        **base_args,
                        "executable_path": system_browser,
                        "args": ["--no-sandbox", "--disable-dev-shm-usage"],
                    },
                )
            )
            log("SYSTEM", f"System browser detected at {system_browser}", "INFO")
        launch_attempts.append(("playwright_default", {**base_args}))
        launch_attempts.append(("playwright_channel_chromium", {**base_args, "channel": "chromium"}))
        launch_attempts.append(("playwright_channel_chrome", {**base_args, "channel": "chrome"}))
    else:
        log("SYSTEM", "Windows detected. Preparing launch strategies.", "INFO")
        if system_browser:
            launch_attempts.append(("system_browser", {**base_args, "executable_path": system_browser}))
            log("SYSTEM", f"System browser detected at {system_browser}", "INFO")
        launch_attempts.append(("playwright_default", {**base_args}))
        launch_attempts.append(("playwright_channel_chromium", {**base_args, "channel": "chromium"}))
        launch_attempts.append(("playwright_channel_chrome", {**base_args, "channel": "chrome"}))
        launch_attempts.append(("playwright_channel_msedge", {**base_args, "channel": "msedge"}))

    last_error = None
    for strategy_name, strategy_args in launch_attempts:
        try:
            log("SYSTEM", f"Launching browser strategy: {strategy_name} (headless={HEADLESS_MODE}).", "INFO")
            browser = await playwright_obj.chromium.launch(**strategy_args)
            log("SYSTEM", f"Browser launch succeeded with strategy: {strategy_name}", "SUCCESS")
            return browser
        except Exception as e:
            last_error = e
            log("SYSTEM", f"Browser launch failed on {strategy_name}: {e}", "ERROR")

    raise RuntimeError(f"All browser launch strategies failed. Last error: {last_error}")

# ==========================================
# FUNÇÕES DE VISÃO E CONTROLE
# ==========================================
def _build_template_variants(template_img):
    variants = []
    base_h, base_w = template_img.shape
    for scale in TEMPLATE_MATCH_SCALES:
        if abs(scale - 1.0) < 1e-9:
            scaled = template_img
        else:
            target_w = max(4, int(round(base_w * scale)))
            target_h = max(4, int(round(base_h * scale)))
            interpolation = cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC
            scaled = cv2.resize(template_img, (target_w, target_h), interpolation=interpolation)
        h, w = scaled.shape
        variants.append((scaled, w, h, scale))
    return variants


def validate_templates():
    required_templates = get_required_templates()
    template_status = {}
    missing_required = []
    all_templates = required_templates + OPTIONAL_TEMPLATES

    for template_name in all_templates:
        template_path = os.path.join(TEMPLATES_DIR, template_name)
        if not os.path.exists(template_path):
            template_status[template_name] = False
            if template_name in required_templates:
                missing_required.append(template_name)
            else:
                log("SYSTEM", f"Optional template missing: {template_name}. Related checks will be skipped.", "WARN")
            continue

        template_img = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        if template_img is None:
            template_status[template_name] = False
            if template_name in required_templates:
                missing_required.append(template_name)
            else:
                log("SYSTEM", f"Optional template unreadable: {template_name}. Related checks will be skipped.", "WARN")
            continue

        TEMPLATE_VARIANTS_CACHE[template_name] = _build_template_variants(template_img)
        template_status[template_name] = True

    if missing_required:
        missing_str = ", ".join(sorted(missing_required))
        raise RuntimeError(f"Required templates unavailable: {missing_str}")

    return template_status


def _get_template_variants(template_name, phone="SYSTEM"):
    cached_variants = TEMPLATE_VARIANTS_CACHE.get(template_name)
    if cached_variants:
        return cached_variants

    template_path = os.path.join(TEMPLATES_DIR, template_name)
    if not os.path.exists(template_path):
        log(phone, f"Template {template_name} not found at {template_path}.", "ERROR")
        return None

    template_img = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    if template_img is None:
        log(phone, f"Template {template_name} could not be loaded by OpenCV.", "ERROR")
        return None

    variants = _build_template_variants(template_img)
    TEMPLATE_VARIANTS_CACHE[template_name] = variants
    return variants


async def match_template(page, template_name, threshold=None, timeout_ms=5000, phone="SYSTEM"):
    effective_threshold = TEMPLATE_THRESHOLDS.get(template_name, DEFAULT_TEMPLATE_THRESHOLD) if threshold is None else threshold
    timeout_seconds = timeout_ms / 1000
    log(phone, f"Searching for {template_name} (timeout: {timeout_seconds:.1f}s, threshold: {effective_threshold:.2f}).", "INFO")

    template_variants = _get_template_variants(template_name, phone=phone)
    if not template_variants:
        return False

    loop = asyncio.get_running_loop()
    start_time = loop.time()
    best_score = -1.0
    best_scale = 1.0
    best_loc = None
    best_size = None
    iteration = 0
    warned_no_fit = False

    while (loop.time() - start_time) < timeout_seconds:
        iteration += 1
        try:
            elapsed = loop.time() - start_time
            log(phone, f"{template_name}: iteration {iteration} (elapsed: {elapsed:.2f}s).", "INFO")

            screenshot_bytes = await page.screenshot()
            nparr = np.frombuffer(screenshot_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            if img is None:
                log(phone, f"{template_name}: screenshot decode failed on iteration {iteration}.", "WARN")
                await asyncio.sleep(0.5)
                continue

            img_h, img_w = img.shape
            current_score = -1.0
            current_loc = None
            current_size = None
            current_scale = 1.0

            for variant_img, w, h, scale in template_variants:
                if w > img_w or h > img_h:
                    continue

                res = cv2.matchTemplate(img, variant_img, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                if max_val > current_score:
                    current_score = float(max_val)
                    current_loc = max_loc
                    current_size = (w, h)
                    current_scale = scale

            if current_score < 0:
                if not warned_no_fit:
                    warned_no_fit = True
                    log(phone, f"{template_name}: no template scale fits screenshot size {img_w}x{img_h}.", "WARN")
                await asyncio.sleep(0.5)
                continue

            if current_score > best_score:
                best_score = current_score
                best_scale = current_scale
                best_loc = current_loc
                best_size = current_size

            log(
                phone,
                f"{template_name}: max score {current_score:.4f} (scale {current_scale:.2f}) vs threshold {effective_threshold:.2f}.",
                "INFO",
            )

            if current_score >= effective_threshold and current_loc and current_size:
                w, h = current_size
                x = int(current_loc[0] + w / 2)
                y = int(current_loc[1] + h / 2)
                log(
                    phone,
                    f"{template_name} matched with score {current_score:.4f} at scale {current_scale:.2f}. Clicking at ({x}, {y}).",
                    "SUCCESS",
                )
                await page.mouse.click(x, y)
                return True
        except Exception as e:
            log(phone, f"{template_name}: exception on iteration {iteration}: {e}", "ERROR")

        await asyncio.sleep(0.5)

    best_score_msg = f"{best_score:.4f}" if best_score >= 0 else "N/A"
    if best_score >= 0:
        log(phone, f"Timeout searching {template_name}. Best score was {best_score_msg} at scale {best_scale:.2f}.", "WARN")
    else:
        log(phone, f"Timeout searching {template_name}. Best score was {best_score_msg}.", "WARN")

    # Debug visual: draw best-match bounding box on last screenshot if available
    try:
        if best_loc and best_size and 'img' in locals() and img is not None:
            debug_dir = os.path.join(BASE_DIR, "analise", "debug")
            os.makedirs(debug_dir, exist_ok=True)
            img_color = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            tl_x, tl_y = int(best_loc[0]), int(best_loc[1])
            w, h = int(best_size[0]), int(best_size[1])
            br_x, br_y = tl_x + w, tl_y + h
            cv2.rectangle(img_color, (tl_x, tl_y), (br_x, br_y), (0, 0, 255), thickness=4)
            file_name = f"debug_mira_{_safe_file_token(template_name)}.png"
            file_path = os.path.join(debug_dir, file_name)
            cv2.imwrite(file_path, img_color)
    except Exception:
        # Never fail the detection flow due to debug image errors
        pass

    return False


def _format_host_for_url(host):
    if ":" in host and not host.startswith("["):
        return f"[{host}]"
    return host


def _normalize_port(port_value):
    try:
        port_int = int(str(port_value).strip())
    except ValueError:
        raise ValueError("port is not numeric")
    if port_int < 1 or port_int > 65535:
        raise ValueError("port is out of range (1-65535)")
    return str(port_int)


def _parse_proxy_entry(proxy_line):
    cleaned = proxy_line.strip()
    if not cleaned:
        raise ValueError("empty line")

    if "://" in cleaned:
        parsed = urlparse(cleaned)
        if not parsed.scheme or not parsed.hostname or not parsed.port:
            raise ValueError("expected URL with scheme://host:port")

        host_for_url = _format_host_for_url(parsed.hostname)
        proxy_config = {"server": f"{parsed.scheme}://{host_for_url}:{parsed.port}"}
        safe_label = f"{parsed.hostname}:{parsed.port}"

        if parsed.username:
            proxy_config["username"] = unquote(parsed.username)
            safe_label = f"{safe_label}:{unquote(parsed.username)}:***"
        if parsed.password:
            proxy_config["password"] = unquote(parsed.password)

        return {"config": proxy_config, "label": safe_label}

    parts = cleaned.split(":")
    if len(parts) == 2:
        host = parts[0].strip()
        port = _normalize_port(parts[1])
        if not host:
            raise ValueError("host is empty")

        host_for_url = _format_host_for_url(host)
        return {
            "config": {"server": f"http://{host_for_url}:{port}"},
            "label": f"{host}:{port}",
        }

    if len(parts) >= 4:
        host = parts[0].strip()
        port = _normalize_port(parts[1])
        username = parts[2].strip()
        password = ":".join(parts[3:]).strip()

        if not host:
            raise ValueError("host is empty")
        if not username:
            raise ValueError("username is empty")
        if not password:
            raise ValueError("password is empty")

        host_for_url = _format_host_for_url(host)
        return {
            "config": {
                "server": f"http://{host_for_url}:{port}",
                "username": username,
                "password": password,
            },
            "label": f"{host}:{port}:{username}:***",
        }

    raise ValueError("unsupported format (use ip:port, ip:port:user:pass or URL)")


def get_proxies():
    if not os.path.exists(PROXIES_FILE):
        return []

    parsed_proxies = []
    invalid_entries = 0

    with open(PROXIES_FILE, "r", encoding="utf-8") as f:
        for line_number, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            try:
                parsed_proxies.append(_parse_proxy_entry(line))
            except ValueError as exc:
                invalid_entries += 1
                log("SYSTEM", f"Ignoring invalid proxy at line {line_number}: {exc}", "WARN")

    if invalid_entries > 0:
        log("SYSTEM", f"Invalid proxies ignored: {invalid_entries}", "WARN")

    return parsed_proxies


async def _click_with_fallback(page, template_name, selectors, phone, timeout_ms=3000, prefer_dom=False):
    if not prefer_dom and await match_template(page, template_name, timeout_ms=timeout_ms, phone=phone):
        return True

    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if await locator.count() == 0:
                continue
            if not await locator.is_visible():
                continue
            await locator.click(timeout=1500)
            log(phone, f"{template_name}: clicked via DOM fallback selector: {selector}", "SUCCESS")
            return True
        except Exception as e:
            log(phone, f"{template_name}: DOM fallback selector failed ({selector}): {e}", "WARN")

    frame_list = list(page.frames)
    for frame_index, frame in enumerate(frame_list):
        if frame is page.main_frame:
            continue
        frame_label = _format_frame_label(frame, frame_index)
        for selector in selectors:
            try:
                locator = frame.locator(selector).first
                if await locator.count() == 0:
                    continue
                if not await locator.is_visible():
                    continue
                await locator.click(timeout=1500)
                log(
                    phone,
                    f"{template_name}: clicked via DOM fallback selector in {frame_label}: {selector}",
                    "SUCCESS",
                )
                return True
            except Exception as e:
                log(phone, f"{template_name}: DOM fallback selector failed in {frame_label} ({selector}): {e}", "WARN")

    if prefer_dom and await match_template(page, template_name, timeout_ms=timeout_ms, phone=phone):
        return True

    return False


def _format_frame_label(frame, frame_index):
    frame_url = "about:blank"
    try:
        frame_url = frame.url or "about:blank"
    except Exception:
        frame_url = "unknown"

    if len(frame_url) > 90:
        frame_url = frame_url[:87] + "..."
    return f"frame#{frame_index}<{frame_url}>"


def _safe_file_token(value):
    if value is None:
        return "unknown"
    sanitized = "".join(ch if (ch.isalnum() or ch in ("-", "_")) else "_" for ch in str(value))
    sanitized = sanitized.strip("_")
    return sanitized or "unknown"


async def _save_debug_screenshot(page, phone, label):
    debug_dir = os.path.join(BASE_DIR, "analise", "debug")
    try:
        os.makedirs(debug_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        file_name = f"{_safe_file_token(phone)}_{_safe_file_token(label)}_{timestamp}.png"
        file_path = os.path.join(debug_dir, file_name)
        await page.screenshot(path=file_path, full_page=True)
        log(phone, f"Debug screenshot saved: {file_path}", "INFO")
        return file_path
    except Exception as e:
        log(phone, f"Debug screenshot capture failed ({label}): {e}", "WARN")
        return None


async def _finalize_attempt_video(page, phone, attempt_number, status_label):
    if not VIDEO_RECORDING_ENABLED:
        return
    if page is None or page.video is None:
        return

    try:
        os.makedirs(VIDEO_OUTPUT_DIR, exist_ok=True)
        raw_video_path = await page.video.path()
    except Exception as e:
        log(phone, f"Video capture warning: could not obtain video path on attempt {attempt_number}: {e}", "WARN")
        return

    if not raw_video_path or not os.path.exists(raw_video_path):
        log(phone, f"Video capture warning: output file not found for attempt {attempt_number}.", "WARN")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    video_name = (
        f"{_safe_file_token(phone)}_attempt{attempt_number:02d}_{_safe_file_token(status_label)}_{timestamp}.webm"
    )
    final_video_path = os.path.join(VIDEO_OUTPUT_DIR, video_name)

    try:
        if os.path.abspath(raw_video_path) != os.path.abspath(final_video_path):
            shutil.move(raw_video_path, final_video_path)
        log(phone, f"Attempt video saved: {final_video_path}", "INFO")
    except Exception as e:
        log(phone, f"Video capture warning: could not move video for attempt {attempt_number}: {e}", "WARN")


async def _log_frame_input_inventory(page, phone, stage_label):
    frame_list = list(page.frames)
    log(phone, f"{stage_label}: frame inventory total={len(frame_list)}.", "INFO")

    inventory_script = """() => {
        const isVisible = (el) => {
            const style = window.getComputedStyle(el)
            const rect = el.getBoundingClientRect()
            return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0
        }

        const collectInputsDeep = () => {
            const allInputs = []
            const queue = [document]
            while (queue.length) {
                const root = queue.shift()
                for (const input of root.querySelectorAll('input')) {
                    allInputs.push(input)
                }
                for (const host of root.querySelectorAll('*')) {
                    if (host.shadowRoot) {
                        queue.push(host.shadowRoot)
                    }
                }
            }
            return allInputs
        }

        const inputs = collectInputsDeep()
        const enabledInputs = inputs.filter((el) => !el.disabled && !el.readOnly)
        const visibleInputs = enabledInputs.filter((el) => isVisible(el))
        const sample = enabledInputs.slice(0, 5).map((el) => {
            const parts = [el.type || '', el.name || '', el.id || '', el.placeholder || '']
            return parts.join('|').toLowerCase()
        })

        return {
            all: inputs.length,
            enabled: enabledInputs.length,
            visible: visibleInputs.length,
            sample,
        }
    }"""

    for frame_index, frame in enumerate(frame_list):
        frame_label = "main_frame" if frame is page.main_frame else _format_frame_label(frame, frame_index)
        try:
            inventory = await frame.evaluate(inventory_script)
            log(
                phone,
                (
                    f"{stage_label}: {frame_label} inputs(all={inventory.get('all')}, "
                    f"enabled={inventory.get('enabled')}, visible={inventory.get('visible')}, "
                    f"sample={inventory.get('sample')})."
                ),
                "INFO",
            )
        except Exception as e:
            log(phone, f"{stage_label}: {frame_label} inventory failed: {e}", "WARN")


async def _has_accessible_registration_inputs(page):
    inventory_script = """() => {
        const isVisible = (el) => {
            const style = window.getComputedStyle(el)
            const rect = el.getBoundingClientRect()
            return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0
        }

        const collectInputsDeep = () => {
            const allInputs = []
            const queue = [document]
            while (queue.length) {
                const root = queue.shift()
                for (const input of root.querySelectorAll('input')) {
                    allInputs.push(input)
                }
                for (const host of root.querySelectorAll('*')) {
                    if (host.shadowRoot) {
                        queue.push(host.shadowRoot)
                    }
                }
            }
            return allInputs
        }

        const inputs = collectInputsDeep().filter((el) => !el.disabled && !el.readOnly)
        const visible = inputs.filter((el) => isVisible(el))
        return { enabledCount: inputs.length, visibleCount: visible.length }
    }"""

    for frame in list(page.frames):
        try:
            result = await frame.evaluate(inventory_script)
            if int(result.get("enabledCount", 0)) > 0 or int(result.get("visibleCount", 0)) > 0:
                return True
        except Exception:
            continue
    return False


async def _fill_registration_via_keyboard_flow(page, phone, phone_value, password_value):
    log(
        phone,
        "Fallback fill: trying visual+keyboard sequence (phone field click + TAB navigation).",
        "WARN",
    )

    phone_anchor_ok = await match_template(
        page,
        "tpl_input_phone.png",
        timeout_ms=PHONE_INPUT_SEARCH_TIMEOUT_MS,
        phone=phone,
    )
    if not phone_anchor_ok:
        log(phone, "Fallback fill failed: phone field anchor template was not found/clicked.", "ERROR")
        return False

    try:
        await page.wait_for_timeout(180)
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await page.keyboard.insert_text(phone_value)
        log(phone, "Fallback fill validated: phone typed via keyboard flow.", "SUCCESS")

        await page.keyboard.press("Tab")
        await page.wait_for_timeout(140)
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await page.keyboard.insert_text(password_value)
        log(phone, "Fallback fill validated: password typed via keyboard flow.", "SUCCESS")

        await page.keyboard.press("Tab")
        await page.wait_for_timeout(140)
        await page.keyboard.press("Control+A")
        await page.keyboard.press("Backspace")
        await page.keyboard.insert_text(password_value)
        log(phone, "Fallback fill validated: password confirmation typed via keyboard flow.", "SUCCESS")
        log(phone, "Passo validado: confirmacao de senha preenchida.", "SUCCESS")
        return True
    except Exception as e:
        log(phone, f"Fallback fill failed while typing: {e}", "ERROR")
        return False


async def wait_for_registration_form_visual_ready(page, phone, timeout_ms=REGISTER_FORM_READY_TIMEOUT_MS):
    timeout_seconds = timeout_ms / 1000
    loop = asyncio.get_running_loop()
    start_time = loop.time()
    iteration = 0

    min_scores = {
        "tpl_input_pass.png": 0.75,
        "tpl_input_pass_confirm.png": 0.75,
        "tpl_btn_inscrever_amarelo.png": 0.75,
    }

    required_templates = tuple(min_scores.keys())

    log(
        phone,
        (
            "Step 5 precheck: waiting visual registration form layout "
            "(password, confirm password, yellow register button)."
        ),
        "INFO",
    )

    while (loop.time() - start_time) < timeout_seconds:
        iteration += 1
        try:
            screenshot_bytes = await page.screenshot()
            nparr = np.frombuffer(screenshot_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            if img is None:
                await asyncio.sleep(0.4)
                continue

            observed = {}
            for template_name in required_templates:
                variants = _get_template_variants(template_name, phone=phone)
                if not variants:
                    observed[template_name] = None
                    continue
                observed[template_name] = _match_template_on_image(img, variants)

            pass_data = observed.get("tpl_input_pass.png")
            confirm_data = observed.get("tpl_input_pass_confirm.png")
            yellow_data = observed.get("tpl_btn_inscrever_amarelo.png")

            score_ok = (
                pass_data
                and confirm_data
                and yellow_data
                and pass_data["score"] >= min_scores["tpl_input_pass.png"]
                and confirm_data["score"] >= min_scores["tpl_input_pass_confirm.png"]
                and yellow_data["score"] >= min_scores["tpl_btn_inscrever_amarelo.png"]
            )

            geometry_ok = False
            if pass_data and confirm_data and yellow_data:
                pass_y = int(pass_data["y"])
                confirm_y = int(confirm_data["y"])
                yellow_y = int(yellow_data["y"])
                geometry_ok = (confirm_y - pass_y) >= 35 and (yellow_y - confirm_y) >= 35

            if score_ok and geometry_ok:
                log(
                    phone,
                    (
                        "Step 5 precheck validated: registration form layout detected "
                        f"(pass_y={int(pass_data['y'])}, confirm_y={int(confirm_data['y'])}, yellow_y={int(yellow_data['y'])})."
                    ),
                    "SUCCESS",
                )
                return True

            if iteration == 1 or iteration % 3 == 0:
                pass_score = f"{pass_data['score']:.4f}" if pass_data else "N/A"
                confirm_score = f"{confirm_data['score']:.4f}" if confirm_data else "N/A"
                yellow_score = f"{yellow_data['score']:.4f}" if yellow_data else "N/A"
                log(
                    phone,
                    (
                        "Step 5 precheck iteration "
                        f"{iteration}: pass={pass_score}, confirm={confirm_score}, yellow={yellow_score}, geometry_ok={geometry_ok}."
                    ),
                    "INFO",
                )
        except Exception as e:
            log(phone, f"Step 5 precheck warning on iteration {iteration}: {e}", "WARN")

        await asyncio.sleep(0.4)

    log(
        phone,
        (
            "Step 5 precheck timeout: registration form visual layout not confirmed "
            "before filling."
        ),
        "WARN",
    )
    # Debug visual: mark observed template positions on last screenshot if available
    try:
        if 'img' in locals() and img is not None:
            debug_dir = os.path.join(BASE_DIR, "analise", "debug")
            os.makedirs(debug_dir, exist_ok=True)
            img_color = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            # observed contains entries for pass, confirm, yellow templates
            for key, data in observed.items():
                try:
                    if not data:
                        continue
                    x = int(data.get("x"))
                    y = int(data.get("y"))
                    # draw a small filled circle at the detected center
                    color = (0, 255, 0) if "pass" in key else (255, 0, 0) if "confirm" in key else (0, 255, 255)
                    cv2.circle(img_color, (x, y), radius=12, color=color, thickness=-1)
                except Exception:
                    continue
            file_path = os.path.join(debug_dir, "debug_step5_layout.png")
            cv2.imwrite(file_path, img_color)
    except Exception:
        pass

    return False


async def _fill_with_fallback(
    page,
    template_name,
    selectors,
    value,
    phone,
    timeout_ms=3000,
    field_kind="text",
    prefer_dom=True,
    allow_template_fallback=True,
):
    dom_fill_script = """({ fieldKind, typedValue }) => {
        const isVisible = (el) => {
            const style = window.getComputedStyle(el)
            const rect = el.getBoundingClientRect()
            return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0
        }

        const collectInputsDeep = () => {
            const allInputs = []
            const queue = [document]
            while (queue.length) {
                const root = queue.shift()
                for (const input of root.querySelectorAll('input')) {
                    allInputs.push(input)
                }
                for (const host of root.querySelectorAll('*')) {
                    if (host.shadowRoot) {
                        queue.push(host.shadowRoot)
                    }
                }
            }
            return allInputs
        }

        const valueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set
        const inputEvent = () => new Event('input', { bubbles: true })
        const changeEvent = () => new Event('change', { bubbles: true })

        const inputs = collectInputsDeep().filter((el) => {
            if (el.disabled || el.readOnly) return false
            return isVisible(el)
        })
        if (!inputs.length) return false

        const meta = (el) => `${el.type || ''} ${el.name || ''} ${el.id || ''} ${el.placeholder || ''}`.toLowerCase()
        const phoneRegex = /(phone|telefone|cel|mobile|whatsapp|numero|number|tel)/
        const passRegex = /(pass|senha|password)/
        const confirmRegex = /(confirm|confirma|repeat|repet|again|verify|verif|re-?pass)/

        let target = null
        if (fieldKind === 'phone') {
            target = inputs.find((el) => phoneRegex.test(meta(el)) || (el.type || '').toLowerCase() === 'tel')
            if (!target) {
                target = inputs.find((el) => (el.type || 'text').toLowerCase() !== 'password')
            }
        } else if (fieldKind === 'password') {
            target = inputs.find((el) => (passRegex.test(meta(el)) || (el.type || '').toLowerCase() === 'password') && !confirmRegex.test(meta(el)))
            if (!target) {
                target = inputs.find((el) => (el.type || '').toLowerCase() === 'password')
            }
        } else if (fieldKind === 'password_confirm') {
            target = inputs.find((el) => (passRegex.test(meta(el)) || (el.type || '').toLowerCase() === 'password') && confirmRegex.test(meta(el)))
            if (!target) {
                const passwordInputs = inputs.filter((el) => passRegex.test(meta(el)) || (el.type || '').toLowerCase() === 'password')
                if (passwordInputs.length >= 2) {
                    target = passwordInputs[1]
                }
            }
        }

        if (!target) return false

        target.focus()
        if (valueSetter) {
            valueSetter.call(target, '')
            target.dispatchEvent(inputEvent())
            valueSetter.call(target, typedValue)
        } else {
            target.value = typedValue
        }

        target.dispatchEvent(inputEvent())
        target.dispatchEvent(changeEvent())
        return true
    }"""

    if not prefer_dom and allow_template_fallback and await match_template(page, template_name, timeout_ms=timeout_ms, phone=phone):
        await page.keyboard.insert_text(value)
        return True

    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if await locator.count() == 0:
                continue
            if not await locator.is_visible():
                continue
            await locator.click(timeout=1500)
            await locator.fill(value, timeout=1500)
            log(phone, f"{template_name}: filled via DOM fallback selector: {selector}", "SUCCESS")
            return True
        except Exception as e:
            log(phone, f"{template_name}: DOM fallback selector failed ({selector}): {e}", "WARN")

    frame_list = list(page.frames)
    for frame_index, frame in enumerate(frame_list):
        if frame is page.main_frame:
            continue
        frame_label = _format_frame_label(frame, frame_index)
        for selector in selectors:
            try:
                locator = frame.locator(selector).first
                if await locator.count() == 0:
                    continue
                if not await locator.is_visible():
                    continue
                await locator.click(timeout=1500)
                await locator.fill(value, timeout=1500)
                log(phone, f"{template_name}: filled via DOM fallback selector in {frame_label}: {selector}", "SUCCESS")
                return True
            except Exception as e:
                log(phone, f"{template_name}: DOM fallback selector failed in {frame_label} ({selector}): {e}", "WARN")

    for frame_index, frame in enumerate(frame_list):
        frame_label = "main_frame" if frame is page.main_frame else _format_frame_label(frame, frame_index)
        try:
            dom_filled = await frame.evaluate(dom_fill_script, {"fieldKind": field_kind, "typedValue": value})
            if dom_filled:
                log(phone, f"{template_name}: filled via DOM evaluate fallback ({field_kind}) in {frame_label}.", "SUCCESS")
                return True
        except Exception as e:
            log(phone, f"{template_name}: DOM evaluate fallback failed ({field_kind}) in {frame_label}: {e}", "WARN")

    if prefer_dom and allow_template_fallback and await match_template(page, template_name, timeout_ms=timeout_ms, phone=phone):
        await page.keyboard.insert_text(value)
        return True

    log(phone, f"{template_name}: fill attempts exhausted (field_kind={field_kind}).", "WARN")
    await _log_frame_input_inventory(page, phone, f"{template_name} fill failure")

    return False


async def validate_registration_values_dom(page, phone, expected_phone, expected_password):
    validation_script = """({ expectedPhone, expectedPassword }) => {
        const isVisible = (el) => {
            const style = window.getComputedStyle(el)
            const rect = el.getBoundingClientRect()
            return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0
        }

        const collectInputsDeep = () => {
            const allInputs = []
            const queue = [document]
            while (queue.length) {
                const root = queue.shift()
                for (const input of root.querySelectorAll('input')) {
                    allInputs.push(input)
                }
                for (const host of root.querySelectorAll('*')) {
                    if (host.shadowRoot) {
                        queue.push(host.shadowRoot)
                    }
                }
            }
            return allInputs
        }

        const sanitizeDigits = (value) => String(value || '').replace(/\\D/g, '')
        const meta = (el) => `${el.type || ''} ${el.name || ''} ${el.id || ''} ${el.placeholder || ''} ${el.autocomplete || ''}`.toLowerCase()
        const phoneRegex = /(phone|telefone|cel|mobile|whatsapp|numero|number|tel)/
        const passRegex = /(pass|senha|password)/
        const confirmRegex = /(confirm|confirma|repeat|repet|again|verify|verif|re-?pass)/

        const inputs = collectInputsDeep().filter((el) => !el.disabled && !el.readOnly)

        const findCandidate = (candidates, fallback = null) => {
            const visible = candidates.find((el) => isVisible(el))
            if (visible) return visible
            if (candidates.length) return candidates[0]
            return fallback
        }

        const phoneCandidates = inputs.filter((el) => phoneRegex.test(meta(el)) || (el.type || '').toLowerCase() === 'tel')
        const genericTextCandidates = inputs.filter((el) => (el.type || 'text').toLowerCase() !== 'password')
        const phoneInput = findCandidate(phoneCandidates, findCandidate(genericTextCandidates, null))

        const passwordInputs = inputs.filter((el) => passRegex.test(meta(el)) || (el.type || '').toLowerCase() === 'password')
        const passwordInput = findCandidate(
            passwordInputs.filter((el) => !confirmRegex.test(meta(el))),
            findCandidate(passwordInputs, null),
        )

        let passConfirmInput = findCandidate(passwordInputs.filter((el) => confirmRegex.test(meta(el))), null)
        if (!passConfirmInput && passwordInputs.length >= 2) {
            passConfirmInput = findCandidate(passwordInputs.filter((el) => el !== passwordInput), null)
        }

        const phoneValue = phoneInput ? String(phoneInput.value || '') : ''
        const passValue = passwordInput ? String(passwordInput.value || '') : ''
        const passConfirmValue = passConfirmInput ? String(passConfirmInput.value || '') : ''

        const expectedPhoneDigits = sanitizeDigits(expectedPhone)
        const actualPhoneDigits = sanitizeDigits(phoneValue)

        const phoneMatches = expectedPhoneDigits
            ? actualPhoneDigits === expectedPhoneDigits || actualPhoneDigits.endsWith(expectedPhoneDigits)
            : actualPhoneDigits.length > 0
        const passwordMatches = expectedPassword ? passValue === expectedPassword : passValue.length > 0
        const passConfirmMatches = expectedPassword ? passConfirmValue === expectedPassword : passConfirmValue.length > 0
        const passwordsEqual = passValue.length > 0 && passValue === passConfirmValue

        return {
            phoneFound: Boolean(phoneInput),
            phoneLength: phoneValue.length,
            phoneDigitsLength: actualPhoneDigits.length,
            phoneMatches,
            passwordFound: Boolean(passwordInput),
            passwordLength: passValue.length,
            passwordMatches,
            passConfirmFound: Boolean(passConfirmInput),
            passConfirmLength: passConfirmValue.length,
            passConfirmMatches,
            passwordsEqual,
        }
    }"""

    frame_list = list(page.frames)
    if not frame_list:
        frame_list = [page.main_frame]

    frame_results = []
    for frame_index, frame in enumerate(frame_list):
        try:
            frame_validation = await frame.evaluate(
                validation_script,
                {"expectedPhone": expected_phone, "expectedPassword": expected_password},
            )
            frame_validation["frameIndex"] = frame_index
            frame_results.append(frame_validation)
        except Exception as e:
            log(phone, f"DOM validation warning in {_format_frame_label(frame, frame_index)}: {e}", "WARN")

    if not frame_results:
        log(phone, "DOM validation failed: no frame could be evaluated.", "ERROR")
        return False

    validation = max(
        frame_results,
        key=lambda data: (
            int(bool(data.get("phoneFound")))
            + int(bool(data.get("passwordFound")))
            + int(bool(data.get("passConfirmFound"))),
            int(bool(data.get("phoneMatches")))
            + int(bool(data.get("passwordMatches")))
            + int(bool(data.get("passConfirmMatches")))
            + int(bool(data.get("passwordsEqual"))),
            int(data.get("phoneLength") or 0)
            + int(data.get("passwordLength") or 0)
            + int(data.get("passConfirmLength") or 0),
        ),
    )

    selected_frame_index = validation.get("frameIndex", -1)
    if 0 <= selected_frame_index < len(frame_list):
        selected_frame_label = _format_frame_label(frame_list[selected_frame_index], selected_frame_index)
    else:
        selected_frame_label = f"frame#{selected_frame_index}"
    log(phone, f"DOM validation source selected: {selected_frame_label}", "INFO")

    if validation.get("phoneFound") and validation.get("phoneMatches"):
        log(
            phone,
            f"DOM validation OK: phone filled (chars={validation.get('phoneLength')}, digits={validation.get('phoneDigitsLength')}).",
            "SUCCESS",
        )
    else:
        log(
            phone,
            f"DOM validation failed for phone (found={validation.get('phoneFound')}, chars={validation.get('phoneLength')}, digits={validation.get('phoneDigitsLength')}).",
            "ERROR",
        )

    if validation.get("passwordFound") and validation.get("passwordMatches"):
        log(
            phone,
            f"DOM validation OK: password filled (len={validation.get('passwordLength')}, hidden).",
            "SUCCESS",
        )
    else:
        log(
            phone,
            f"DOM validation failed for password (found={validation.get('passwordFound')}, len={validation.get('passwordLength')}).",
            "ERROR",
        )

    if validation.get("passConfirmFound") and validation.get("passConfirmMatches") and validation.get("passwordsEqual"):
        log(
            phone,
            (
                "DOM validation OK: password confirmation filled "
                f"(len={validation.get('passConfirmLength')}, matches_password={validation.get('passwordsEqual')})."
            ),
            "SUCCESS",
        )
    else:
        log(
            phone,
            (
                "DOM validation failed for password confirmation "
                f"(found={validation.get('passConfirmFound')}, len={validation.get('passConfirmLength')}, "
                f"matches_password={validation.get('passwordsEqual')})."
            ),
            "ERROR",
        )

    return (
        validation.get("phoneFound")
        and validation.get("phoneMatches")
        and validation.get("passwordFound")
        and validation.get("passwordMatches")
        and validation.get("passConfirmFound")
        and validation.get("passConfirmMatches")
        and validation.get("passwordsEqual")
    )


def _match_template_on_image(img, template_variants):
    img_h, img_w = img.shape
    best_score = -1.0
    best_loc = None
    best_size = None
    best_scale = 1.0

    for variant_img, w, h, scale in template_variants:
        if w > img_w or h > img_h:
            continue

        res = cv2.matchTemplate(img, variant_img, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val > best_score:
            best_score = float(max_val)
            best_loc = max_loc
            best_size = (w, h)
            best_scale = scale

    if best_score < 0 or best_loc is None or best_size is None:
        return None

    w, h = best_size
    x = int(best_loc[0] + w / 2)
    y = int(best_loc[1] + h / 2)
    return {"score": best_score, "x": x, "y": y, "scale": best_scale}


async def run_initial_gate_step(page, phone, timeout_ms=8000):
    gate_templates = ("tpl_btn_ok_1010.png", "tpl_btn_engrenagem.png")
    timeout_seconds = timeout_ms / 1000
    loop = asyncio.get_running_loop()
    start_time = loop.time()
    iteration = 0
    best_observed = {}

    log(
        phone,
        "Step 1: probing initial gate (tpl_btn_ok_1010.png vs tpl_btn_engrenagem.png).",
        "INFO",
    )

    while (loop.time() - start_time) < timeout_seconds:
        iteration += 1
        try:
            elapsed = loop.time() - start_time
            log(phone, f"Initial gate: iteration {iteration} (elapsed: {elapsed:.2f}s).", "INFO")

            screenshot_bytes = await page.screenshot()
            nparr = np.frombuffer(screenshot_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            if img is None:
                log(phone, "Initial gate: screenshot decode failed.", "WARN")
                await asyncio.sleep(0.4)
                continue

            passing_candidates = []
            for template_name in gate_templates:
                template_variants = _get_template_variants(template_name, phone=phone)
                if not template_variants:
                    continue

                match_data = _match_template_on_image(img, template_variants)
                if not match_data:
                    continue

                threshold = TEMPLATE_THRESHOLDS.get(template_name, DEFAULT_TEMPLATE_THRESHOLD)
                score = match_data["score"]
                x = match_data["x"]
                y = match_data["y"]
                scale = match_data["scale"]

                previous_best = best_observed.get(template_name)
                if previous_best is None or score > previous_best["score"]:
                    best_observed[template_name] = {
                        "score": score,
                        "threshold": threshold,
                        "x": x,
                        "y": y,
                        "scale": scale,
                    }

                log(
                    phone,
                    f"Initial gate {template_name}: score {score:.4f} (scale {scale:.2f}) vs threshold {threshold:.2f} at ({x}, {y}).",
                    "INFO",
                )

                if score >= threshold:
                    passing_candidates.append(
                        {
                            "template_name": template_name,
                            "score": score,
                            "threshold": threshold,
                            "x": x,
                            "y": y,
                            "scale": scale,
                        }
                    )

            if passing_candidates:
                selected = max(
                    passing_candidates,
                    key=lambda candidate: ((candidate["score"] - candidate["threshold"]), candidate["score"]),
                )
                await page.mouse.move(selected["x"], selected["y"])
                await page.mouse.click(selected["x"], selected["y"])
                log(
                    phone,
                    (
                        f"Step 1 hit: selected {selected['template_name']} "
                        f"with score {selected['score']:.4f} (threshold {selected['threshold']:.2f}) "
                        f"at ({selected['x']}, {selected['y']})."
                    ),
                    "SUCCESS",
                )
                return selected

        except Exception as e:
            log(phone, f"Initial gate exception on iteration {iteration}: {e}", "ERROR")

        await asyncio.sleep(0.4)

    if best_observed:
        best_parts = []
        for template_name in gate_templates:
            data = best_observed.get(template_name)
            if data:
                best_parts.append(f"{template_name}={data['score']:.4f}/{data['threshold']:.2f}")
        best_text = ", ".join(best_parts) if best_parts else "none"
        log(phone, f"Step 1 timeout: no template passed threshold. Best observed: {best_text}", "WARN")
    else:
        log(phone, "Step 1 timeout: no valid template observations collected.", "WARN")

    return None


def generate_random_phone():
    valid_ddds = [ddd for ddd in range(11, 100) if str(ddd)[1] != '0']
    ddd = random.choice(valid_ddds)
    return f"{ddd}9{random.randint(10000000, 99999999)}"


async def run_logout_step_after_gear(page, phone, require_confirm=False, require_register=False):
    log(phone, f"Step 2: waiting guest popup before logout click ({LOGOUT_POPUP_WAIT_MS}ms).", "INFO")
    await page.wait_for_timeout(LOGOUT_POPUP_WAIT_MS)

    logout_selectors = [
        'button:has-text("Sair")',
        'a:has-text("Sair")',
        "text=Sair",
        'button:has-text("Logout")',
        'a:has-text("Logout")',
        "text=Logout",
    ]

    clicked_logout = await _click_with_fallback(
        page,
        "tpl_btn_sair.png",
        logout_selectors,
        phone,
        timeout_ms=LOGOUT_SEARCH_TIMEOUT_MS,
        prefer_dom=False,
    )
    if not clicked_logout:
        log(phone, "Step 2 failed: logout option was not found/clicked.", "ERROR")
        return False

    log(phone, "Step 2 validated: logout option clicked.", "SUCCESS")

    if not require_confirm:
        return True

    log(phone, f"Step 3: waiting confirm popup before confirmation click ({LOGOUT_CONFIRM_POPUP_WAIT_MS}ms).", "INFO")
    await page.wait_for_timeout(LOGOUT_CONFIRM_POPUP_WAIT_MS)

    confirm_selectors = [
        'button:has-text("Confirmar")',
        'a:has-text("Confirmar")',
        "text=Confirmar",
        'button:has-text("OK")',
        'a:has-text("OK")',
        "text=OK",
        'button:has-text("Sim")',
        'a:has-text("Sim")',
        "text=Sim",
    ]

    clicked_confirm = await _click_with_fallback(
        page,
        "tpl_btn_confirmar.png",
        confirm_selectors,
        phone,
        timeout_ms=LOGOUT_CONFIRM_SEARCH_TIMEOUT_MS,
        prefer_dom=False,
    )
    if clicked_confirm:
        log(phone, "Step 3 validated: logout confirmation clicked.", "SUCCESS")
    else:
        log(phone, "Step 3 failed: logout confirmation was not found/clicked.", "ERROR")
        return False

    if not require_register:
        return True

    log(phone, f"Step 4: waiting post-logout refresh before register click ({REGISTER_ENTRY_POPUP_WAIT_MS}ms).", "INFO")
    await page.wait_for_timeout(REGISTER_ENTRY_POPUP_WAIT_MS)

    clicked_register = await match_template(
        page,
        "tpl_btn_inscrever.png",
        timeout_ms=REGISTER_ENTRY_SEARCH_TIMEOUT_MS,
        phone=phone,
    )
    if clicked_register:
        log(phone, "Step 4 validated: register entry button clicked.", "SUCCESS")
        return True

    log(phone, "Step 4 failed: register entry button was not found/clicked.", "ERROR")
    return False


async def run_registration_form_steps(page, phone, require_submit=False):
    log(phone, f"Step 5: waiting registration form before filling ({REGISTER_FORM_POPUP_WAIT_MS}ms).", "INFO")
    await page.wait_for_timeout(REGISTER_FORM_POPUP_WAIT_MS)

    form_ready = await wait_for_registration_form_visual_ready(
        page,
        phone,
        timeout_ms=REGISTER_FORM_READY_TIMEOUT_MS,
    )
    if not form_ready:
        await _save_debug_screenshot(page, phone, "step5_form_precheck_timeout")
        log(phone, "Step 5 failed: registration form visual layout was not confirmed.", "ERROR")
        return False

    used_keyboard_fallback = False

    phone_input_selectors = [
        "input[type='tel']",
        "input[name*='phone' i]",
        "input[id*='phone' i]",
        "input[placeholder*='phone' i]",
        "input[name*='telefone' i]",
        "input[id*='telefone' i]",
        "input[placeholder*='telefone' i]",
        "input[inputmode='numeric']",
        "input[type='text']",
    ]
    phone_input_ok = await _fill_with_fallback(
        page,
        "tpl_input_phone.png",
        phone_input_selectors,
        phone,
        phone,
        timeout_ms=PHONE_INPUT_SEARCH_TIMEOUT_MS,
        field_kind="phone",
        prefer_dom=False,
        allow_template_fallback=True,
    )
    if not phone_input_ok:
        log(phone, "Step 5 warning: phone input was not found/filled via DOM. Trying keyboard fallback.", "WARN")
        await _save_debug_screenshot(page, phone, "step5_dom_fill_not_found")

        used_keyboard_fallback = await _fill_registration_via_keyboard_flow(
            page,
            phone,
            phone_value=phone,
            password_value=REGISTER_PASSWORD,
        )
        if not used_keyboard_fallback:
            log(phone, "Step 5 failed: phone input was not found/filled.", "ERROR")
            await _save_debug_screenshot(page, phone, "step5_fill_failed")
            return False
        log(phone, "Step 5 validated: fallback keyboard flow completed.", "SUCCESS")
    else:
        log(phone, "Step 5 validated: phone input filled.", "SUCCESS")

        pass_input_selectors = [
            "input[name*='pass' i]:not([name*='confirm' i]):not([name*='confirma' i])",
            "input[id*='pass' i]:not([id*='confirm' i]):not([id*='confirma' i])",
            "input[placeholder*='pass' i]:not([placeholder*='confirm' i]):not([placeholder*='confirma' i])",
            "input[name*='senha' i]:not([name*='confirm' i]):not([name*='confirma' i])",
            "input[id*='senha' i]:not([id*='confirm' i]):not([id*='confirma' i])",
            "input[placeholder*='senha' i]:not([placeholder*='confirm' i]):not([placeholder*='confirma' i])",
            "input[type='password']",
        ]
        pass_input_ok = await _fill_with_fallback(
            page,
            "tpl_input_pass.png",
            pass_input_selectors,
            REGISTER_PASSWORD,
            phone,
            timeout_ms=PASS_INPUT_SEARCH_TIMEOUT_MS,
            field_kind="password",
            prefer_dom=False,
            allow_template_fallback=True,
        )
        if not pass_input_ok:
            log(phone, "Step 6 warning: password input was not found/filled via DOM. Trying keyboard fallback.", "WARN")
            await _save_debug_screenshot(page, phone, "step6_dom_fill_not_found")
            used_keyboard_fallback = await _fill_registration_via_keyboard_flow(
                page,
                phone,
                phone_value=phone,
                password_value=REGISTER_PASSWORD,
            )
            if not used_keyboard_fallback:
                log(phone, "Step 6 failed: password input was not found/filled.", "ERROR")
                await _save_debug_screenshot(page, phone, "step6_fill_failed")
                return False
            log(phone, "Step 6 validated: fallback keyboard flow completed.", "SUCCESS")
        else:
            log(phone, "Step 6 validated: password input filled.", "SUCCESS")

            pass_confirm_input_selectors = [
                "input[name*='confirm' i]",
                "input[id*='confirm' i]",
                "input[placeholder*='confirm' i]",
                "input[name*='confirma' i]",
                "input[id*='confirma' i]",
                "input[placeholder*='confirma' i]",
                "input[name*='repeat' i]",
                "input[id*='repeat' i]",
                "input[placeholder*='repeat' i]",
            ]
            pass_confirm_input_ok = await _fill_with_fallback(
                page,
                "tpl_input_pass_confirm.png",
                pass_confirm_input_selectors,
                REGISTER_PASSWORD,
                phone,
                timeout_ms=PASS_CONFIRM_INPUT_SEARCH_TIMEOUT_MS,
                field_kind="password_confirm",
                prefer_dom=False,
                allow_template_fallback=True,
            )
            if not pass_confirm_input_ok:
                log(phone, "Step 7 warning: password confirmation input was not found/filled via DOM. Trying keyboard fallback.", "WARN")
                await _save_debug_screenshot(page, phone, "step7_dom_fill_not_found")
                used_keyboard_fallback = await _fill_registration_via_keyboard_flow(
                    page,
                    phone,
                    phone_value=phone,
                    password_value=REGISTER_PASSWORD,
                )
                if not used_keyboard_fallback:
                    log(phone, "Step 7 failed: password confirmation input was not found/filled.", "ERROR")
                    await _save_debug_screenshot(page, phone, "step7_fill_failed")
                    return False
                log(phone, "Step 7 validated: fallback keyboard flow completed.", "SUCCESS")
            else:
                log(phone, "Step 7 validated: password confirmation input filled.", "SUCCESS")
                log(phone, "Passo validado: confirmacao de senha preenchida.", "SUCCESS")

    # Skip DOM validation and proceed directly to submit step

    if not require_submit:
        return True

    submit_selectors = [
        "button[type='submit']",
        "form button:has-text('Inscrever')",
        "form button:has-text('Cadastrar')",
        'button:has-text("Cadastrar")',
        'button:has-text("Inscrever")',
        'button:has-text("Registrar")',
        "text=Confirmar",
    ]
    submit_ok = await _click_with_fallback(
        page,
        "tpl_btn_inscrever_amarelo.png",
        submit_selectors,
        phone,
        timeout_ms=FINAL_REGISTER_BUTTON_SEARCH_TIMEOUT_MS,
        prefer_dom=False,
    )
    if not submit_ok:
        log(phone, "Step 8 failed: final yellow register button was not found/clicked.", "ERROR")
        return False
    log(phone, "Step 8 validated: final yellow register button clicked.", "SUCCESS")
    log(phone, "Passo validado: botao Inscrever amarelo clicado.", "SUCCESS")

    return True


async def ensure_registration_tab_ready(page, phone):
    log(phone, "Keep-alive: garantindo aba/formulario de Inscrever antes do novo cadastro.", "INFO")

    clicked_register = await match_template(
        page,
        "tpl_btn_inscrever.png",
        timeout_ms=REGISTER_ENTRY_SEARCH_TIMEOUT_MS,
        phone=phone,
    )
    if not clicked_register:
        await _save_debug_screenshot(page, phone, "keep_alive_register_tab_not_found")
        log(phone, "Keep-alive failed: aba/botao Inscrever nao foi encontrado.", "ERROR")
        return False

    log(phone, "Keep-alive: aba/botao Inscrever clicado; aguardando formulario de cadastro.", "SUCCESS")
    await page.wait_for_timeout(REGISTER_FORM_POPUP_WAIT_MS)

    form_ready = await wait_for_registration_form_visual_ready(
        page,
        phone,
        timeout_ms=REGISTER_FORM_READY_TIMEOUT_MS,
    )
    if not form_ready:
        await _save_debug_screenshot(page, phone, "keep_alive_registration_form_not_ready")
        log(phone, "Keep-alive failed: formulario de Inscrever nao ficou visualmente pronto.", "ERROR")
        return False

    log(phone, "Keep-alive: formulario de Inscrever pronto para novo cadastro.", "SUCCESS")
    return True


async def detect_success_deposit_button(page, phone, timeout_ms=5000):
    template_name = "tpl_btn_deposito.png"
    template_variants = _get_template_variants(template_name, phone=phone)
    if not template_variants:
        log(phone, f"Success proof template unavailable: {template_name}", "ERROR")
        return False

    timeout_seconds = timeout_ms / 1000
    loop = asyncio.get_running_loop()
    start_time = loop.time()

    while (loop.time() - start_time) < timeout_seconds:
        try:
            screenshot_bytes = await page.screenshot()
            nparr = np.frombuffer(screenshot_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            if img is None:
                await asyncio.sleep(0.4)
                continue

            match_data = _match_template_on_image(img, template_variants)
            if match_data and match_data["score"] >= TEMPLATE_THRESHOLDS.get(template_name, DEFAULT_TEMPLATE_THRESHOLD):
                log(phone, "Success proof validated: deposit button detected.", "SUCCESS")
                return True
        except Exception as e:
            log(phone, f"Success proof detection warning: {e}", "WARN")

        await asyncio.sleep(0.4)

    return False


async def wait_and_capture_post_registration(page, phone, run_1010_checks=False):
    async def click_first_available_template(step_label, template_names, timeout_ms):
        for template_name in template_names:
            template_path = os.path.join(TEMPLATES_DIR, template_name)
            if not os.path.exists(template_path):
                log(phone, f"{step_label}: template ausente, tentando fallback: {template_name}", "WARN")
                continue

            if await match_template(page, template_name, timeout_ms=timeout_ms, phone=phone):
                log(phone, f"{step_label}: clicado via {template_name}.", "SUCCESS")
                return True

        log(phone, f"{step_label}: nenhum template foi encontrado/clicado: {template_names}", "ERROR")
        return False

    log(phone, "Aguardando carregamento completo apos cadastro...", "INFO")
    await page.wait_for_load_state("networkidle")
    log(phone, "Carregamento pos-cadastro: networkidle recebido.", "SUCCESS")

    await page.wait_for_timeout(8000)

    os.makedirs("debug", exist_ok=True)

    screenshot_path = os.path.join("debug", "tela_pos_cadastro.png")
    await page.screenshot(path=screenshot_path, full_page=True)
    log(phone, f"Screenshot pos-cadastro salvo em {screenshot_path}", "SUCCESS")

    if run_1010_checks and await match_template(page, "tpl_btn_ok_1010.png", timeout_ms=3000, phone=phone):
        log(phone, "Late 1010 detected after submit.", "WARN")
        return "blocked_1010"

    if not await click_first_available_template("Passo pos-cadastro 1: fechar bonus", ("tpl_btn_fechar_bonus.png",), 9000):
        await _save_debug_screenshot(page, phone, "post_registration_close_bonus_not_found")
        return False
    with open(SUCCESS_FILE, "a", encoding="utf-8") as f:
        f.write(f"{phone}\n")
    log(phone, f"Conta criada com sucesso, numero salvo: {phone}", "INFO")
    await page.wait_for_timeout(2000)

    if not await click_first_available_template("Passo pos-cadastro 2: abrir menu", ("tpl_btn_engrenagem.png",), 9000):
        await _save_debug_screenshot(page, phone, "post_registration_gear_not_found")
        return False
    await page.wait_for_timeout(1000)

    if not await click_first_available_template("Passo pos-cadastro 3: sair", ("tpl_btn_sair_config.png", "tpl_btn_sair.png"), 9000):
        await _save_debug_screenshot(page, phone, "post_registration_logout_not_found")
        return False
    await page.wait_for_timeout(1000)

    if not await click_first_available_template("Passo pos-cadastro 4: confirmar logout", ("tpl_btn_confirmar_sair.png", "tpl_btn_confirmar.png"), 9000):
        await _save_debug_screenshot(page, phone, "post_registration_confirm_logout_not_found")
        return False

    await page.wait_for_load_state("networkidle")
    log(phone, "Tela inicial recarregada apos logout.", "SUCCESS")

    if not await click_first_available_template("Passo pos-cadastro 5: abrir formulario inicial", ("tpl_btn_inscrever.png",), REGISTER_ENTRY_SEARCH_TIMEOUT_MS):
        await _save_debug_screenshot(page, phone, "post_registration_register_entry_not_found")
        return False

    log(phone, "Fluxo pos-cadastro concluido: formulario inicial reaberto.", "SUCCESS")
    return "success"


async def run_post_success_logout_cycle(page, phone):
    if not await match_template(page, "tpl_btn_engrenagem.png", timeout_ms=LOGOUT_SEARCH_TIMEOUT_MS, phone=phone):
        await _save_debug_screenshot(page, phone, "post_success_gear_not_found")
        log(phone, "Post-success logout failed: gear button was not found/clicked.", "ERROR")
        return False

    await page.wait_for_timeout(LOGOUT_POPUP_WAIT_MS)

    if not await match_template(page, "tpl_btn_sair.png", timeout_ms=LOGOUT_SEARCH_TIMEOUT_MS, phone=phone):
        await _save_debug_screenshot(page, phone, "post_success_logout_not_found")
        log(phone, "Post-success logout failed: logout button was not found/clicked.", "ERROR")
        return False

    await page.wait_for_timeout(LOGOUT_CONFIRM_POPUP_WAIT_MS)

    if not await match_template(page, "tpl_btn_confirmar.png", timeout_ms=LOGOUT_CONFIRM_SEARCH_TIMEOUT_MS, phone=phone):
        await _save_debug_screenshot(page, phone, "post_success_confirm_not_found")
        log(phone, "Post-success logout failed: confirm button was not found/clicked.", "ERROR")
        return False

    await page.wait_for_timeout(REGISTER_ENTRY_POPUP_WAIT_MS)

    if not await match_template(page, "tpl_btn_inscrever.png", timeout_ms=REGISTER_ENTRY_SEARCH_TIMEOUT_MS, phone=phone):
        await _save_debug_screenshot(page, phone, "post_success_register_not_found")
        log(phone, "Post-success logout failed: register entry button was not found/clicked.", "ERROR")
        return False

    log(phone, "Post-success logout cycle validated: register entry reopened.", "SUCCESS")
    return True


async def wait_for_page_readiness(page, phone):
    log(phone, "Waiting for page readiness signals before gate scan...", "INFO")

    try:
        await page.wait_for_load_state("domcontentloaded", timeout=PAGE_READY_TIMEOUT_MS)
        log(phone, "Page readiness: domcontentloaded signal received.", "INFO")
    except Exception as e:
        log(phone, f"Page readiness warning on domcontentloaded: {e}", "WARN")

    try:
        await page.wait_for_selector("body", state="visible", timeout=5000)
        log(phone, "Page readiness: body is visible.", "INFO")
    except Exception as e:
        log(phone, f"Page readiness warning on body visibility: {e}", "WARN")

    try:
        await page.wait_for_function(
            "document.readyState === 'complete' || document.readyState === 'interactive'",
            timeout=PAGE_READY_TIMEOUT_MS,
        )
        log(phone, "Page readiness: DOM readyState is interactive/complete.", "INFO")
    except Exception as e:
        log(phone, f"Page readiness warning on readyState: {e}", "WARN")

    try:
        await page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_TIMEOUT_MS)
        log(phone, "Page readiness: networkidle signal received.", "INFO")
    except Exception as e:
        log(phone, f"Page readiness warning on networkidle: {e}", "WARN")

    log(phone, f"Waiting final UI stabilization ({INITIAL_PAGE_STABILIZATION_MS}ms).", "INFO")
    await page.wait_for_timeout(INITIAL_PAGE_STABILIZATION_MS)
    log(phone, "Page readiness complete. Starting element detection.", "SUCCESS")

# ==========================================
# O WORKER INTELIGENTE
# ==========================================
async def worker(phone, semaphore, playwright_obj, proxy_list, template_status):
    async with semaphore:
        total_attempts = MAX_PROXY_RETRIES_PER_PHONE + 1
        if FLOW_MODE in (
            "initial_gate_only",
            "gear_only",
            "gear_logout_only",
            "gear_logout_confirm_only",
            "gear_logout_confirm_register_only",
            "gear_logout_confirm_register_inputs_only",
            "gear_logout_confirm_register_form_only",
        ) and proxy_list:
            total_attempts = max(total_attempts, len(proxy_list) + 1)

        log(phone, f"Worker started. Max attempts: {total_attempts}.", "INFO")
        run_1010_checks = template_status.get("tpl_btn_ok_1010.png", False)
        if not run_1010_checks:
            log(phone, "tpl_btn_ok_1010.png unavailable. 1010 checks disabled for this worker.", "WARN")

        active_proxy_list = list(proxy_list)
        current_proxy_slot = -1

        def _refresh_proxy_pool_from_active_list():
            nonlocal current_proxy_slot
            if not active_proxy_list:
                current_proxy_slot = -1
                return

            if current_proxy_slot >= len(active_proxy_list):
                current_proxy_slot = -1

        def _reload_proxy_list_if_needed(reason):
            nonlocal active_proxy_list, current_proxy_slot
            if active_proxy_list:
                return True

            reloaded_proxies = get_proxies()
            if reloaded_proxies:
                active_proxy_list = list(reloaded_proxies)
                current_proxy_slot = -1
                log(phone, f"{reason} Proxy list exhausted. Reloaded {len(active_proxy_list)} proxies from file.", "WARN")
                return True

            log(phone, f"{reason} Fim da lista de proxies.", "ERROR")
            return False

        if active_proxy_list:
            try:
                shuffled_labels = [proxy["label"] for proxy in random.sample(active_proxy_list, len(active_proxy_list))]
                log(phone, f"Shuffled proxy order: {', '.join(shuffled_labels)}", "INFO")
            except Exception:
                pass

        def _current_route_label():
            if current_proxy_slot < 0 or not active_proxy_list:
                return "Clean IP"
            return active_proxy_list[current_proxy_slot]["label"]

        def _rotate_to_next_proxy(reason):
            nonlocal active_proxy_list, current_proxy_slot

            failed_label = _current_route_label()
            failed_proxy = None
            if current_proxy_slot >= 0 and current_proxy_slot < len(active_proxy_list):
                failed_proxy = active_proxy_list[current_proxy_slot]

            if failed_proxy is not None and "1010" in reason:
                active_proxy_list = [proxy for proxy in active_proxy_list if proxy is not failed_proxy]
                current_proxy_slot = -1
                log(phone, f"{reason} Proxy banido da lista ativa: {failed_label}.", "WARN")

            _refresh_proxy_pool_from_active_list()
            if not _reload_proxy_list_if_needed(reason):
                return False

            previous_label = _current_route_label()

            try:
                chosen = random.randrange(len(active_proxy_list))
                current_proxy_slot = chosen
            except Exception:
                current_proxy_slot = 0 if active_proxy_list else -1

            next_label = _current_route_label()
            log(phone, f"{reason} Rotating route: {previous_label} -> {next_label}.", "WARN")
            return True

        for attempt in range(total_attempts):
            if not _reload_proxy_list_if_needed("Attempt startup."):
                break

            if current_proxy_slot < 0 and active_proxy_list:
                try:
                    current_proxy_slot = random.randrange(len(active_proxy_list))
                except Exception:
                    current_proxy_slot = 0

            current_proxy = None
            if current_proxy_slot >= 0 and active_proxy_list:
                current_proxy = active_proxy_list[current_proxy_slot]["config"]

            if current_proxy is not None:
                log(
                    phone,
                    f"Attempt {attempt + 1}/{total_attempts}: using Proxy {_current_route_label()} (slot {current_proxy_slot + 1}/{len(active_proxy_list)}).",
                    "INFO",
                )
            else:
                log(phone, f"Attempt {attempt + 1}/{total_attempts}: using Clean IP (no proxy).", "INFO")

            context = None
            browser = None
            page = None
            attempt_video_status = "retry"
            try:
                log(phone, "Launching browser for current proxy session...", "INFO")
                browser = await launch_browser_multi_os(playwright_obj)

                log(phone, "Creating browser context...", "INFO")
                context_options = {
                    "proxy": current_proxy,
                    "viewport": {"width": 1366, "height": 768},
                    "device_scale_factor": 1,
                    "color_scheme": "light",
                }
                

                context = await browser.new_context(**context_options)
                log(phone, "Opening new page...", "INFO")
                page = await context.new_page()
                if VIDEO_RECORDING_ENABLED and page.video is not None:
                    log(phone, f"Attempt {attempt + 1}: video recording enabled.", "INFO")

                log(phone, f"Navigating to target URL: {TARGET_URL}", "INFO")
                await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30000)
                await wait_for_page_readiness(page, phone)

                form_ready_for_registration = False
                while True:
                    phone = generate_random_phone()
                    log(phone, f"Starting keep-alive registration cycle on route {_current_route_label()}.", "INFO")

                    if form_ready_for_registration and FLOW_MODE == "gear_logout_confirm_register_form_only":
                        if not await ensure_registration_tab_ready(page, phone):
                            attempt_video_status = "retry_registration_tab_not_ready"
                            log(phone, "Keep-alive registration tab transition failed. Breaking current proxy session.", "ERROR")
                            break

                        if await run_registration_form_steps(page, phone, require_submit=True):
                            post_registration_status = await wait_and_capture_post_registration(
                                page,
                                phone,
                                run_1010_checks=run_1010_checks,
                            )
                            if post_registration_status == "success":
                                form_ready_for_registration = True
                                continue

                            if post_registration_status == "blocked_1010":
                                attempt_video_status = "rotate_1010_late"
                                _rotate_to_next_proxy("Late 1010 detected after submit.")
                                break

                            attempt_video_status = "retry_post_registration_visual_flow_failed"
                            log(phone, "Post-registration visual flow failed. Breaking current proxy session.", "ERROR")
                            break

                        attempt_video_status = "retry_form_sequence_failed"
                        log(phone, "Keep-alive form sequence failed. Breaking current proxy session.", "ERROR")
                        break

                    initial_gate = await run_initial_gate_step(page, phone, timeout_ms=INITIAL_GATE_TIMEOUT_MS)
                    if not initial_gate:
                        attempt_video_status = "retry_gate_not_matched"
                        log(
                            phone,
                            "Step 1 failed: neither tpl_btn_ok_1010 nor tpl_btn_engrenagem passed threshold. Breaking current session.",
                            "ERROR",
                        )
                        break

                    selected_template = initial_gate["template_name"]

                    if selected_template == "tpl_btn_ok_1010.png":
                        attempt_video_status = "rotate_1010_initial"
                        if not _rotate_to_next_proxy("Initial gate detected 1010."):
                            break
                        break

                    if FLOW_MODE in (
                        "gear_logout_only",
                        "gear_logout_confirm_only",
                        "gear_logout_confirm_register_only",
                        "gear_logout_confirm_register_inputs_only",
                        "gear_logout_confirm_register_form_only",
                    ):
                        require_confirm = FLOW_MODE in (
                            "gear_logout_confirm_only",
                            "gear_logout_confirm_register_only",
                            "gear_logout_confirm_register_inputs_only",
                            "gear_logout_confirm_register_form_only",
                        )
                        require_register = FLOW_MODE in (
                            "gear_logout_confirm_register_only",
                            "gear_logout_confirm_register_inputs_only",
                            "gear_logout_confirm_register_form_only",
                        )
                        require_inputs = FLOW_MODE in (
                            "gear_logout_confirm_register_inputs_only",
                            "gear_logout_confirm_register_form_only",
                        )
                        require_submit = FLOW_MODE == "gear_logout_confirm_register_form_only"

                        if await run_logout_step_after_gear(
                            page,
                            phone,
                            require_confirm=require_confirm,
                            require_register=require_register,
                        ):
                            if require_inputs:
                                if await run_registration_form_steps(page, phone, require_submit=require_submit):
                                    post_registration_status = await wait_and_capture_post_registration(
                                        page,
                                        phone,
                                        run_1010_checks=run_1010_checks,
                                    )
                                    if post_registration_status == "success":
                                        form_ready_for_registration = True
                                        continue

                                    if post_registration_status == "blocked_1010":
                                        attempt_video_status = "rotate_1010_late"
                                        _rotate_to_next_proxy("Late 1010 detected after submit.")
                                        break

                                    attempt_video_status = "retry_post_registration_visual_flow_failed"
                                    log(phone, "FLOW_MODE=gear_logout_confirm_register_form_only: post-registration visual flow failed.", "ERROR")
                                    break

                                attempt_video_status = "retry_form_sequence_failed"
                                log(phone, f"FLOW_MODE={FLOW_MODE}: form sequence failed. Breaking current session.", "ERROR")
                                break

                            attempt_video_status = "success"
                            log(phone, f"FLOW_MODE={FLOW_MODE}: steps validated, finishing worker.", "SUCCESS")
                            return True

                        attempt_video_status = "retry_validation_sequence_failed"
                        log(phone, f"FLOW_MODE={FLOW_MODE}: validation sequence failed. Breaking current session.", "ERROR")
                        break

                    if FLOW_MODE in ("initial_gate_only", "gear_only"):
                        attempt_video_status = "success"
                        log(
                            phone,
                            f"FLOW_MODE={FLOW_MODE}: step validated by {selected_template}, finishing worker.",
                            "SUCCESS",
                        )
                        return True

                    # 2. Bypass da Sessão Logada (Logout via Engrenagem)
                    guest_menu_already_open = selected_template == "tpl_btn_engrenagem.png"
                    log(phone, "Checking Guest Login...", "INFO")
                    if guest_menu_already_open or await match_template(page, "tpl_btn_engrenagem.png", timeout_ms=3000, phone=phone):
                        log(phone, "Guest session detected. Forcing logout sequence.", "WARN")
                        await asyncio.sleep(1)
                        log(phone, "Clicking logout option...", "INFO")
                        if not await match_template(page, "tpl_btn_sair.png", timeout_ms=3000, phone=phone):
                            await _save_debug_screenshot(page, phone, "legacy_logout_not_found")
                            attempt_video_status = "retry_logout_not_found"
                            break
                        await asyncio.sleep(1)
                        log(phone, "Clicking logout confirmation...", "INFO")
                        if not await match_template(page, "tpl_btn_confirmar.png", timeout_ms=3000, phone=phone):
                            await _save_debug_screenshot(page, phone, "legacy_confirm_not_found")
                            attempt_video_status = "retry_logout_confirm_not_found"
                            break
                        log(phone, "Waiting page refresh after logout (4000ms).", "INFO")
                        await page.wait_for_timeout(4000)

                    # 3. Porta da Frente (Cadastro)
                    log(phone, "Checking registration entry button...", "INFO")
                    if not await match_template(page, "tpl_btn_inscrever.png", timeout_ms=7000, phone=phone):
                        await _save_debug_screenshot(page, phone, "legacy_register_not_found")
                        log(phone, "Critical error: Register button not found. Breaking current session.", "ERROR")
                        attempt_video_status = "retry_register_not_found"
                        break

                    # Preenchimento com fallback visual + DOM
                    log(phone, "Filling phone input...", "INFO")
                    phone_input_selectors = [
                        "input[type='tel']",
                        "input[name*='phone' i]",
                        "input[id*='phone' i]",
                        "input[placeholder*='phone' i]",
                        "input[name*='telefone' i]",
                        "input[id*='telefone' i]",
                        "input[placeholder*='telefone' i]",
                        "input[inputmode='numeric']",
                        "input[type='text']",
                    ]
                    phone_input_ok = await _fill_with_fallback(
                        page,
                        "tpl_input_phone.png",
                        phone_input_selectors,
                        phone,
                        phone,
                        timeout_ms=3000,
                        field_kind="phone",
                        prefer_dom=True,
                    )
                    if not phone_input_ok:
                        await _save_debug_screenshot(page, phone, "legacy_phone_fill_failed")
                        log(phone, "Phone input was not found by template or DOM fallback. Breaking current session.", "ERROR")
                        attempt_video_status = "retry_phone_fill_failed"
                        break

                    log(phone, "Filling password input...", "INFO")
                    pass_input_selectors = [
                        "input[name*='pass' i]:not([name*='confirm' i]):not([name*='confirma' i])",
                        "input[id*='pass' i]:not([id*='confirm' i]):not([id*='confirma' i])",
                        "input[placeholder*='pass' i]:not([placeholder*='confirm' i]):not([placeholder*='confirma' i])",
                        "input[name*='senha' i]:not([name*='confirm' i]):not([name*='confirma' i])",
                        "input[id*='senha' i]:not([id*='confirm' i]):not([id*='confirma' i])",
                        "input[placeholder*='senha' i]:not([placeholder*='confirm' i]):not([placeholder*='confirma' i])",
                        "input[type='password']",
                    ]
                    pass_input_ok = await _fill_with_fallback(
                        page,
                        "tpl_input_pass.png",
                        pass_input_selectors,
                        REGISTER_PASSWORD,
                        phone,
                        timeout_ms=3000,
                        field_kind="password",
                        prefer_dom=True,
                    )
                    if not pass_input_ok:
                        await _save_debug_screenshot(page, phone, "legacy_pass_fill_failed")
                        log(phone, "Password input was not found by template or DOM fallback. Breaking current session.", "ERROR")
                        attempt_video_status = "retry_pass_fill_failed"
                        break

                    log(phone, "Filling password confirmation input...", "INFO")
                    pass_confirm_input_selectors = [
                        "input[name*='confirm' i]",
                        "input[id*='confirm' i]",
                        "input[placeholder*='confirm' i]",
                        "input[name*='confirma' i]",
                        "input[id*='confirma' i]",
                        "input[placeholder*='confirma' i]",
                        "input[name*='repeat' i]",
                        "input[id*='repeat' i]",
                        "input[placeholder*='repeat' i]",
                    ]
                    pass_confirm_input_ok = await _fill_with_fallback(
                        page,
                        "tpl_input_pass_confirm.png",
                        pass_confirm_input_selectors,
                        REGISTER_PASSWORD,
                        phone,
                        timeout_ms=3000,
                        field_kind="password_confirm",
                        prefer_dom=True,
                    )
                    if not pass_confirm_input_ok:
                        await _save_debug_screenshot(page, phone, "legacy_pass_confirm_fill_failed")
                        log(phone, "Password confirmation input was not found by template or DOM fallback. Breaking current session.", "ERROR")
                        attempt_video_status = "retry_pass_confirm_fill_failed"
                        break

                    dom_values_ok = await validate_registration_values_dom(
                        page,
                        phone,
                        expected_phone=phone,
                        expected_password=REGISTER_PASSWORD,
                    )
                    if not dom_values_ok:
                        await _save_debug_screenshot(page, phone, "legacy_dom_validation_failed")
                        log(phone, "DOM validation failed for phone/password/password_confirmation. Breaking current session.", "ERROR")
                        attempt_video_status = "retry_dom_validation_failed"
                        break

                    log(phone, "Clicking final yellow register button...", "INFO")
                    submit_selectors = [
                        "button[type='submit']",
                        "form button:has-text('Inscrever')",
                        "form button:has-text('Cadastrar')",
                        'button:has-text("Cadastrar")',
                        'button:has-text("Inscrever")',
                        'button:has-text("Registrar")',
                        "text=Confirmar",
                    ]
                    submit_found = await _click_with_fallback(
                        page,
                        "tpl_btn_inscrever_amarelo.png",
                        submit_selectors,
                        phone,
                        timeout_ms=3000,
                        prefer_dom=True,
                    )
                    if not submit_found:
                        await _save_debug_screenshot(page, phone, "legacy_submit_not_found")
                        log(phone, "Final yellow register action not found by template or DOM fallback. Breaking current session.", "ERROR")
                        attempt_video_status = "retry_submit_not_found"
                        break

                    log(phone, "Passo validado: botao Inscrever amarelo clicado.", "SUCCESS")

                    post_registration_status = await wait_and_capture_post_registration(
                        page,
                        phone,
                        run_1010_checks=run_1010_checks,
                    )
                    if post_registration_status == "success":
                        continue

                    if post_registration_status == "blocked_1010":
                        attempt_video_status = "rotate_1010_late"
                        _rotate_to_next_proxy("Late 1010 detected after submit.")
                        break

                    attempt_video_status = "retry_post_registration_visual_flow_failed"
                    log(phone, "Post-registration visual flow failed. Breaking current session.", "ERROR")
                    break

                    
                if attempt_video_status == "success":
                    return True

                if attempt_video_status.startswith("rotate_1010"):
                    continue

                continue

            except Exception as e:
                attempt_video_status = "exception"
                log(phone, f"Flow exception on attempt {attempt + 1}: {e}", "ERROR")
            finally:
                if context is not None:
                    log(phone, f"Closing context for attempt {attempt + 1}.", "INFO")
                    try:
                        await context.close()
                    except Exception as e:
                        log(phone, f"Context close warning on attempt {attempt + 1}: {e}", "WARN")
                if browser is not None:
                    log(phone, f"Closing browser for attempt {attempt + 1}.", "INFO")
                    try:
                        await browser.close()
                    except Exception as e:
                        log(phone, f"Browser close warning on attempt {attempt + 1}: {e}", "WARN")

                

        log(phone, "FAILURE: Maximum retries exhausted.", "ERROR")

# ==========================================
# DISPATCHER MAIN (MULTI-OS)
# ==========================================
async def main():
    log("SYSTEM", "Starting production batch execution.", "INFO")
    log("SYSTEM", f"Flow mode active: {FLOW_MODE}", "INFO")

    if VIDEO_RECORDING_ENABLED:
        os.makedirs(VIDEO_OUTPUT_DIR, exist_ok=True)
        log("SYSTEM", f"Attempt video recording enabled at: {VIDEO_OUTPUT_DIR}", "INFO")

    required_templates = get_required_templates()
    template_status = validate_templates()
    log(
        "SYSTEM",
        f"Templates validated. required={len(required_templates)} optional_enabled={sum(1 for name in OPTIONAL_TEMPLATES if template_status.get(name))}/{len(OPTIONAL_TEMPLATES)}",
        "INFO",
    )

    proxy_list = get_proxies()
    log("SYSTEM", f"Loaded proxies: {len(proxy_list)}", "INFO")

    phones_to_register = [generate_random_phone() for _ in range(5)]
    log("SYSTEM", f"Phones queued for processing: {len(phones_to_register)}", "INFO")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_BROWSERS)

    async with async_playwright() as p:
        try:
            log("SYSTEM", "Starting worker task batch.", "INFO")
            tasks = [worker(phone, semaphore, p, proxy_list, template_status) for phone in phones_to_register]
            results = await asyncio.gather(*tasks)
            success_count = sum(1 for result in results if result)
            log("SYSTEM", f"Worker batch completed. Success count: {success_count}/{len(phones_to_register)}", "SUCCESS")
        except Exception as e:
            log("SYSTEM", f"Fatal error in main flow: {e}", "ERROR")
            log(
                "SYSTEM",
                "If browser executable is missing, run: python -m playwright install chromium",
                "WARN",
            )
            raise
    log("SYSTEM", "Batch execution finished.", "SUCCESS")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("SYSTEM", "Execution interrupted by user (Ctrl+C).", "WARN")
