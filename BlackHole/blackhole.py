# BlackHole - маленькие чёрные дыры вокруг игрока.
# Линзирование фона, горизонт событий, два кольца, аккреционный диск с линзированным
# вторым образом, красное смещение, полярные струи, пыль, искры, вспышки рождения
# и смерти, низкий гул.

import math
import random
import time

MAX = 8  # столько дыр держат массивы шейдера

mod = Module("BlackHole", "Visuals")
mod.setDesc("Чёрные дыры вокруг игрока: линзирование, диск, струи, гул")

Info(mod, "Дыры")
m_mode = Mode(mod, "Режим").add("Россыпь").add("Одна большая")
s_count = Slider(mod, "Сколько дыр").min(1).max(6).step(1).set(3)
s_radius = Slider(mod, "Радиус вокруг игрока").min(4).max(40).step(1).set(14).suffix(" бл.")
s_spread = Slider(mod, "Разброс по высоте").min(0).max(10).step(0.5).set(3)
s_size = Slider(mod, "Размер").min(0.1).max(1.5).step(0.05).set(0.4)
s_life = Slider(mod, "Время жизни").min(2).max(30).step(1).set(9).suffix(" с")
s_delay = Slider(mod, "Пауза между рождениями").min(0.1).max(6).step(0.1).set(1.2).suffix(" с")

Info(mod, "Искривление")
b_warp = Checkbox(mod, "Искривлять пространство").set(True)
s_warp = Slider(mod, "Сила искривления").min(0.2).max(3).step(0.1).set(1.2)
b_chroma = Checkbox(mod, "Радуга на краю").set(True)
b_shadow = Checkbox(mod, "Горизонт событий").set(True)

Info(mod, "Картинка")
b_disk = Checkbox(mod, "Аккреционный диск").set(True)
b_echo = Checkbox(mod, "Второй образ диска").set(True)
b_ring = Checkbox(mod, "Фотонные кольца").set(True)
b_red = Checkbox(mod, "Красное смещение").set(True)
b_bloom = Checkbox(mod, "Свечение").set(True)
b_jets = Checkbox(mod, "Полярные струи").set(True)
b_dust = Checkbox(mod, "Падающая пыль").set(True)
b_sparks = Checkbox(mod, "Искры внутрь").set(True)
s_glow = Slider(mod, "Яркость").min(0.2).max(3).step(0.1).set(1)
g_disk = Gradient(mod, "Цвет диска").set(Color(255, 238, 205), Color(255, 108, 34)).alpha(False)
c_halo = ColorSetting(mod, "Цвет гало").color(130, 100, 255).alpha(False)

Info(mod, "Гул")
b_hum = Checkbox(mod, "Звук").set(True)
t_hum = TextSetting(mod, "Файл").maxLength(120).set("blackhole_rumble.ogg")
s_hum = Slider(mod, "Громкость").min(0).max(1).step(0.05).set(0.7)

Info(mod, "Вручную")
k_spawn = Bind(mod, "Дыра по взгляду").set("G")
s_look = Slider(mod, "Дальность").min(2).max(48).step(1).set(14).suffix(" бл.")
s_look_size = Slider(mod, "Размер ручной").min(0.2).max(6).step(0.1).set(1.2)
btn_clear = Button(mod, "Убрать все")

HOLES = []
SEEN = set()
STATE = {"next": 0.0, "hum": None, "hum_path": "", "hum_bad": False, "vol": 0.0}


def note(msg):
    key = str(msg)[:140]
    if key in SEEN:
        return
    SEEN.add(key)
    print("[BlackHole] " + key)


def hex01(color, fallback):
    try:
        raw = color.toHex().lstrip("#")
        return (int(raw[0:2], 16) / 255.0, int(raw[2:4], 16) / 255.0, int(raw[4:6], 16) / 255.0)
    except Exception:
        return fallback


def disk_colors():
    inner = (1.0, 0.93, 0.80)
    outer = (1.0, 0.42, 0.13)
    try:
        inner = hex01(g_disk.getFirst(), inner)
        outer = hex01(g_disk.getSecond(), outer)
    except Exception as ex:
        note("градиент не читается: " + str(ex))
    return (inner, outer)


def halo_color():
    try:
        return hex01(c_halo.get(), (0.51, 0.39, 1.0))
    except Exception:
        return (0.51, 0.39, 1.0)


def is_big():
    return m_mode.get() == "Одна большая"


def want_count():
    return 1 if is_big() else int(s_count.get())


def eff_radius():
    return s_radius.get() * (1.6 if is_big() else 1.0)


def eff_size():
    return s_size.get() * (6.0 if is_big() else 1.0)


def eff_life():
    return s_life.get() * (3.0 if is_big() else 1.0)


def make_hole(x, y, z, rs, life, now, manual=False):
    return {
        "x": x, "y": y, "z": z, "rs": rs,
        "born": now, "life": life, "manual": manual,
        "spin": random.uniform(0.0, math.tau),
        "tilt": random.uniform(-0.9, 0.9),
        "orbit": random.uniform(0.25, 0.7) * random.choice((-1.0, 1.0)),
        "bob": random.uniform(0.6, 1.4),
        "drift": random.uniform(0.2, 0.9),
    }


def push(hole):
    HOLES.append(hole)
    while len(HOLES) > MAX:
        HOLES.pop(0)


def spawn_random(me, now):
    ang = random.uniform(0.0, math.tau)
    dist = eff_radius() * (0.35 + 0.65 * random.random())
    hole = make_hole(
        me.getX() + math.cos(ang) * dist,
        me.getY() + 1.4 + random.uniform(0.0, s_spread.get()),
        me.getZ() + math.sin(ang) * dist,
        eff_size() * random.uniform(0.7, 1.35),
        eff_life() * random.uniform(0.8, 1.2),
        now,
    )
    if is_big():
        hole["drift"] *= 0.25
        hole["bob"] *= 0.4
    push(hole)


def look_point(me, reach):
    yaw = math.radians(me.getYaw())
    pitch = math.radians(me.getPitch())
    cp = math.cos(pitch)
    dx = -math.sin(yaw) * cp
    dy = -math.sin(pitch)
    dz = math.cos(yaw) * cp
    ox, oy, oz = me.getX(), me.getY() + 1.62, me.getZ()
    best = (ox + dx * 0.8, oy + dy * 0.8, oz + dz * 0.8)
    steps = int(max(reach - 0.8, 0.0) / 0.5)
    for i in range(1, steps + 1):
        t = 0.8 + 0.5 * i
        px, py, pz = ox + dx * t, oy + dy * t, oz + dz * t
        try:
            blocked = world.is_solid(int(math.floor(px)), int(math.floor(py)), int(math.floor(pz)))
        except Exception:
            blocked = False
        if blocked:
            break
        best = (px, py, pz)
    return best


def spawn_look():
    if not world.ingame():
        return False
    me = world.self()
    if me is None:
        return False
    now = time.time()
    x, y, z = look_point(me, s_look.get())
    hole = make_hole(x, y, z, s_look_size.get(), eff_life() * 1.5, now, manual=True)
    hole["drift"] *= 0.2
    hole["bob"] *= 0.5
    push(hole)
    return True


def hole_pos(hole, now):
    age = now - hole["born"]
    turn = hole["spin"] + age * hole["orbit"]
    return (
        hole["x"] + math.cos(turn) * hole["drift"],
        hole["y"] + math.sin(age * hole["bob"]) * 0.35,
        hole["z"] + math.sin(turn) * hole["drift"],
    )


def hole_fade(hole, now):
    age = now - hole["born"]
    left = hole["life"] - age
    if age < 0.0 or left <= 0.0:
        return 0.0
    f = min(1.0, age / 0.9) * min(1.0, left / 1.4)
    return f * f * (3.0 - 2.0 * f)


def hole_flash(hole, now):
    age = now - hole["born"]
    left = hole["life"] - age
    if age < 0.0 or left <= 0.0:
        return 0.0
    birth = max(0.0, 1.0 - age / 0.45)
    death = max(0.0, 1.0 - left / 0.55)
    return min(max(birth * birth, death * death * 1.2), 1.4)


def active_holes(now):
    out = []
    for hole in HOLES:
        fade = hole_fade(hole, now)
        if fade <= 0.0:
            continue
        x, y, z = hole_pos(hole, now)
        rs = hole["rs"] * (0.4 + 0.6 * fade)  # горизонт раскрывается и схлопывается
        out.append((hole, x, y, z, rs, fade, hole_flash(hole, now)))
    return out


def disk_frame(tilt):
    nx, ny, nz = math.sin(tilt) * 0.5, 1.0, math.cos(tilt) * 0.5
    ln = math.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx / ln, ny / ln, nz / ln
    ax, ay, az = ny, -nx, 0.0
    la = math.sqrt(ax * ax + ay * ay + az * az)
    if la < 1e-6:
        ax, ay, az, la = 1.0, 0.0, 0.0, 1.0
    ax, ay, az = ax / la, ay / la, az / la
    return (nx, ny, nz, ax, ay, az, ny * az - nz * ay, nz * ax - nx * az, nx * ay - ny * ax)


def dust_of(out, hole, x, y, z, rs, now, fade, gain, inner_c, outer_c):
    horizon = rs * 2.6
    near = horizon * 1.15
    far = horizon * 4.4
    nx, ny, nz, ax, ay, az, bx, by, bz = disk_frame(hole["tilt"])
    base = (now - hole["born"]) * 1.1 + hole["spin"]
    for j in range(12):
        ph = (base * 0.35 + j / 12.0) % 1.0
        alpha = 205.0 * fade * gain * math.sin(math.pi * ph)
        if alpha < 6.0:
            continue
        r1 = near + (far - near) * ((1.0 - ph) ** 1.6)
        r2 = r1 + (far - near) * 0.05 * (1.0 - ph)
        a1 = base * (1.3 + 1.9 * (1.0 - ph)) + j * 2.399963
        a2 = a1 - (0.18 + 0.25 * (1.0 - ph))
        c1, s1 = math.cos(a1), math.sin(a1)
        c2, s2 = math.cos(a2), math.sin(a2)
        heat = (1.0 - ph) ** 1.5
        out.extend((
            x + (ax * c1 + bx * s1) * r1,
            y + (ay * c1 + by * s1) * r1,
            z + (az * c1 + bz * s1) * r1,
            x + (ax * c2 + bx * s2) * r2,
            y + (ay * c2 + by * s2) * r2,
            z + (az * c2 + bz * s2) * r2,
            (outer_c[0] + (inner_c[0] - outer_c[0]) * heat) * 255.0,
            (outer_c[1] + (inner_c[1] - outer_c[1]) * heat) * 255.0,
            (outer_c[2] + (inner_c[2] - outer_c[2]) * heat) * 255.0,
            min(alpha, 255.0),
        ))


def spark_point(hole, x, y, z, rs, j, ph):
    horizon = rs * 2.6
    near = horizon * 0.95
    far = horizon * 5.5
    k = min(max(ph, 0.0), 1.0)
    rr = near + (far - near) * ((1.0 - k) ** 1.8)
    ang = j * 2.399963 + hole["spin"] + (1.0 - k) * 2.4
    ele = math.sin(j * 1.7 + hole["tilt"]) * 1.15
    ce = math.cos(ele)
    return (x + math.cos(ang) * ce * rr, y + math.sin(ele) * rr, z + math.sin(ang) * ce * rr)


def sparks_of(out, hole, x, y, z, rs, now, fade, gain, halo):
    base = (now - hole["born"]) * 0.55
    for j in range(10):
        ph = (base + j * 0.1) % 1.0
        alpha = 235.0 * fade * gain * math.sin(math.pi * ph)
        if alpha < 6.0:
            continue
        x1, y1, z1 = spark_point(hole, x, y, z, rs, j, ph)
        x2, y2, z2 = spark_point(hole, x, y, z, rs, j, ph - 0.06)
        white = ph ** 2
        out.extend((
            x1, y1, z1, x2, y2, z2,
            (halo[0] + (1.0 - halo[0]) * white) * 255.0,
            (halo[1] + (1.0 - halo[1]) * white) * 255.0,
            (halo[2] + (1.0 - halo[2]) * white) * 255.0,
            min(alpha, 255.0),
        ))


def jets_of(out, hole, x, y, z, rs, now, fade, gain, inner_c, halo):
    horizon = rs * 2.6
    nx, ny, nz, ax, ay, az, bx, by, bz = disk_frame(hole["tilt"])
    age = now - hole["born"]
    for side in (1.0, -1.0):
        for i in range(7):
            tip = i / 7.0
            alpha = 215.0 * fade * gain * ((1.0 - tip) ** 1.4) * (0.72 + 0.28 * math.sin(age * 6.0 - i * 0.8))
            if alpha < 6.0:
                continue
            t1 = horizon * (0.9 + i * 0.95)
            t2 = horizon * (0.9 + (i + 1) * 0.95)
            w1 = horizon * 0.1 * (1.0 + i * 0.3)
            w2 = horizon * 0.1 * (1.0 + (i + 1) * 0.3)
            p1 = age * 3.1 * side + i * 0.85 + hole["spin"]
            p2 = p1 + 0.85
            c1, s1 = math.cos(p1), math.sin(p1)
            c2, s2 = math.cos(p2), math.sin(p2)
            out.extend((
                x + nx * side * t1 + (ax * c1 + bx * s1) * w1,
                y + ny * side * t1 + (ay * c1 + by * s1) * w1,
                z + nz * side * t1 + (az * c1 + bz * s1) * w1,
                x + nx * side * t2 + (ax * c2 + bx * s2) * w2,
                y + ny * side * t2 + (ay * c2 + by * s2) * w2,
                z + nz * side * t2 + (az * c2 + bz * s2) * w2,
                (inner_c[0] + (halo[0] - inner_c[0]) * tip) * 255.0,
                (inner_c[1] + (halo[1] - inner_c[1]) * tip) * 255.0,
                (inner_c[2] + (halo[2] - inner_c[2]) * tip) * 255.0,
                min(alpha, 255.0),
            ))


def hum_stop():
    track = STATE["hum"]
    STATE["hum"] = None
    STATE["vol"] = 0.0
    if track is None:
        return
    try:
        track.stop()
    except Exception:
        pass


def hum_wanted(me, holes):
    if not b_hum.get() or STATE["hum_bad"] or t_hum.isEmpty() or not holes:
        return 0.0
    mx, my, mz = me.getX(), me.getY() + 1.4, me.getZ()
    span = max(eff_radius() * 2.0, 8.0)
    best = 0.0
    for hole, hx, hy, hz, rs, fade, flash in holes:
        dx, dy, dz = hx - mx, hy - my, hz - mz
        d = math.sqrt(dx * dx + dy * dy + dz * dz)
        near = 1.0 - min(d / span, 1.0)
        loud = fade * near * near * min(1.0, rs * 1.8)
        if loud > best:
            best = loud
    return best * s_hum.get()


def hum_apply(vol):
    if vol <= 0.002:
        hum_stop()
        return
    path = t_hum.get()
    track = STATE["hum"]
    if track is not None and STATE["hum_path"] != path:
        hum_stop()
        track = None
    if track is None:
        try:
            STATE["hum"] = sound.loop(path, volume=vol, category="ambient")
            STATE["hum_path"] = path
        except Exception as ex:
            STATE["hum_bad"] = True
            note("гул не завёлся (" + str(path) + "): " + str(ex))
        return
    try:
        track.volume(vol)
    except Exception:
        STATE["hum"] = None


def clear_all():
    del HOLES[:]
    hum_stop()


btn_clear.action(clear_all)


GLSL = """
uniform vec4 Holes[8];
uniform vec4 Extra[8];
uniform float Count;
uniform float Warp;
uniform float Chroma;
uniform float DiskOn;
uniform float EchoOn;
uniform float RingOn;
uniform float RedOn;
uniform float BloomOn;
uniform float ShadowOn;
uniform float Glow;
uniform vec3 TintIn;
uniform vec3 TintOut;
uniform vec3 Halo;

vec2 dirToUv(mat4 vp, vec3 d, vec2 fallback) {
    vec4 c = vp * vec4(d * 16.0, 1.0);
    if (c.w <= 0.0001) return fallback;
    return clamp(c.xy / c.w * 0.5 + 0.5, vec2(0.0015), vec2(0.9985));
}

vec3 diskSample(vec3 rd, vec3 pos, vec3 n, float horizon, float spin, float maxT) {
    float dn = dot(rd, n);
    if (abs(dn) < 0.002) return vec3(0.0);
    float t = dot(pos, n) / dn;
    if (t <= 0.0 || t >= maxT) return vec3(0.0);
    vec3 q = rd * t - pos;
    float inner = horizon * 1.25;
    float outer = horizon * 4.6;
    float k = (length(q) - inner) / (outer - inner);
    if (k <= 0.0 || k >= 1.0) return vec3(0.0);
    vec3 t1 = normalize(cross(n, vec3(0.0, 0.0, 1.0)));
    vec3 t2 = cross(n, t1);
    float ang = atan(dot(q, t2), dot(q, t1));
    float band = smoothstep(0.0, 0.10, k) * (1.0 - smoothstep(0.5, 1.0, k));
    float swirl = 0.55 + 0.45 * sin(ang * 3.0 - spin * 2.4 + k * 14.0);
    float fine = 0.72 + 0.28 * sin(k * 46.0 - spin * 3.4);
    float doppler = 0.40 + 0.60 * pow(0.5 + 0.5 * sin(ang - spin * 0.6), 1.6);
    return mix(TintIn, TintOut, pow(k, 0.7)) * band * swirl * fine * doppler;
}

void main() {
    vec2 uv = FragCoord;
    vec3 background = texture(Sampler0, uv).rgb;
    vec2 ndc = uv * 2.0 - 1.0;

    vec4 farPoint = InvViewProj * vec4(ndc, 1.0, 1.0);
    vec3 dir = normalize(farPoint.xyz / farPoint.w);

    float depth = texture(Sampler1, uv).r;
    float sceneDist = 4096.0;
    if (depth < 0.9999) {
        vec4 scenePoint = InvViewProj * vec4(ndc, depth * 2.0 - 1.0, 1.0);
        sceneDist = length(scenePoint.xyz / scenePoint.w);
    }

    vec3 bend = vec3(0.0);
    vec3 disk = vec3(0.0);
    float lens = 0.0;
    float shadow = 0.0;
    float ring = 0.0;
    float haze = 0.0;
    float red = 0.0;

    for (int i = 0; i < 8; i++) {
        if (float(i) >= Count) break;

        vec3 pos = Holes[i].xyz;
        float rs = Holes[i].w;
        float fade = Extra[i].x;
        float spin = Extra[i].y;
        float flash = Extra[i].w;
        if (rs <= 0.0 || fade <= 0.0) continue;

        float along = dot(dir, pos);
        if (along <= 0.0) continue;

        float dist = length(pos);
        float visible = 1.0 - smoothstep(sceneDist, sceneDist + 1.0, dist);
        if (visible <= 0.0) continue;

        vec3 perp = pos - dir * along;
        float b = max(length(perp), 0.0005);
        vec3 toward = perp / b;
        float horizon = rs * 2.6;
        float live = fade * visible;

        if (Warp > 0.001) {
            float defl = min(Warp * 2.0 * rs / b, 1.5) * live;
            bend += toward * defl;
            lens += defl;
        }

        float aa = max(dist * 0.006, 0.012);
        float core = 1.0 - smoothstep(horizon - aa, horizon + aa, b);
        if (ShadowOn > 0.5) {
            shadow = max(shadow, core * live);
        }

        if (RingOn > 0.5) {
            float rw = max(horizon * 0.13, 0.015);
            float dr = (b - horizon * 1.05) / rw;
            ring += exp(-dr * dr) * live * (1.0 + flash * 4.0);
            float dr2 = (b - horizon * 1.42) / max(horizon * 0.42, 0.05);
            ring += exp(-dr2 * dr2) * live * 0.26;
        }

        haze += live * (horizon * horizon) / (b * b + horizon * horizon * 1.4) * (1.0 - core) * (1.0 + flash * 2.0);

        if (RedOn > 0.5) {
            red = max(red, live * (1.0 - smoothstep(horizon, horizon * 3.2, b)) * (1.0 - core));
        }

        if (DiskOn > 0.5) {
            vec3 n = normalize(vec3(sin(Extra[i].z) * 0.5, 1.0, cos(Extra[i].z) * 0.5));
            float maxT = min(sceneDist, 160.0);
            disk += diskSample(dir, pos, n, horizon, spin, maxT) * (live * 1.35);
            if (EchoOn > 0.5 && Warp > 0.001) {
                vec3 bent = normalize(dir + toward * min(Warp * 3.6 * rs / b, 2.4));
                disk += diskSample(bent, pos, n, horizon, spin, maxT) * (live * 0.7);
            }
        }
    }

    vec3 color = background;

    if (lens > 0.0005) {
        mat4 viewProj = ProjMat * ModelViewMat;
        vec2 probe = dirToUv(viewProj, dir, vec2(-1.0));
        if (probe.x < 0.0 || distance(probe, uv) > 0.02) {
            viewProj = inverse(InvViewProj);
        }
        vec3 warped;
        if (Chroma > 0.5) {
            vec2 uvR = dirToUv(viewProj, normalize(dir + bend * 1.12), uv);
            vec2 uvG = dirToUv(viewProj, normalize(dir + bend), uv);
            vec2 uvB = dirToUv(viewProj, normalize(dir + bend * 0.88), uv);
            warped = vec3(texture(Sampler0, uvR).r, texture(Sampler0, uvG).g, texture(Sampler0, uvB).b);
        } else {
            warped = texture(Sampler0, dirToUv(viewProj, normalize(dir + bend), uv)).rgb;
        }
        color = mix(background, warped, clamp(lens * 8.0, 0.0, 1.0));
        color *= 1.0 - 0.5 * clamp(lens * 0.7, 0.0, 1.0);
    }

    if (red > 0.001) {
        color = mix(color, color * vec3(1.25, 0.55, 0.32), clamp(red, 0.0, 1.0) * 0.75);
    }

    color = mix(color, vec3(0.0), clamp(shadow, 0.0, 1.0));
    color += TintIn * ring * 1.45 * Glow;
    color += Halo * haze * 0.45 * Glow;
    color += disk * Glow;

    if (BloomOn > 0.5) {
        float bright = max(max(color.r, color.g), color.b);
        color += TintIn * pow(clamp(bright - 0.9, 0.0, 1.6), 1.8) * 0.16;
    }

    fragColor = vec4(color, 1.0);
}
"""

lensing = Shader("blackhole_lens", GLSL)


@events.tick
def on_tick(event):
    try:
        if not mod.isEnabled():
            if HOLES:
                del HOLES[:]
            if STATE["hum"] is not None:
                hum_stop()
            return
        if not world.ingame():
            return
        me = world.self()
        if me is None:
            return

        now = time.time()
        mx, my, mz = me.getX(), me.getY(), me.getZ()
        limit = eff_radius() * 2.2 + 8.0
        for hole in list(HOLES):
            if now - hole["born"] >= hole["life"]:
                HOLES.remove(hole)
                continue
            dx, dy, dz = hole["x"] - mx, hole["y"] - my, hole["z"] - mz
            if dx * dx + dy * dy + dz * dz > limit * limit:
                HOLES.remove(hole)

        want = min(want_count(), MAX)
        autos = [hole for hole in HOLES if not hole["manual"]]
        while len(autos) > want:
            HOLES.remove(autos.pop(0))
        if len(autos) < want and now >= STATE["next"]:
            spawn_random(me, now)
            STATE["next"] = now + s_delay.get()

        goal = hum_wanted(me, active_holes(now))
        STATE["vol"] = STATE["vol"] + (goal - STATE["vol"]) * 0.18
        hum_apply(STATE["vol"])
    except Exception as ex:
        note(str(ex))


@events.key
def on_key(event):
    try:
        if not mod.isEnabled() or not k_spawn.isSet():
            return
        if not event.isPress() or not k_spawn.isKey(event.getKey()):
            return
        if spawn_look():
            client.msg("[BlackHole] дыра создана")
    except Exception as ex:
        note(str(ex))


@events.world_change
def on_world(event):
    clear_all()


@events.render_3d
def on_render(event):
    if not mod.isEnabled() or not HOLES:
        return
    try:
        if not world.ingame():
            return

        now = time.time()
        camera = event.getCamera().getPos()
        cx, cy, cz = camera.x, camera.y, camera.z
        inner_c, outer_c = disk_colors()
        halo = halo_color()
        gain = s_glow.get()
        want_dust = b_dust.get()
        want_sparks = b_sparks.get()
        want_jets = b_jets.get()

        streaks = []
        shown = 0
        for hole, x, y, z, rs, fade, flash in active_holes(now):
            if shown >= MAX:
                break
            lensing.set("Holes[%d]" % shown, x - cx, y - cy, z - cz, rs)
            lensing.set(
                "Extra[%d]" % shown,
                fade,
                hole["spin"] + (now - hole["born"]) * 1.6,
                hole["tilt"],
                flash,
            )
            shown += 1
            if want_dust:
                dust_of(streaks, hole, x, y, z, rs, now, fade, gain, inner_c, outer_c)
            if want_sparks:
                sparks_of(streaks, hole, x, y, z, rs, now, fade, gain, halo)
            if want_jets:
                jets_of(streaks, hole, x, y, z, rs, now, fade, gain, inner_c, halo)

        if shown == 0:
            return

        if streaks:
            render3d.lines(event, streaks, True, through=False)

        warp = s_warp.get() if b_warp.get() else 0.0
        lensing.set("Count", float(shown))
        lensing.set("Warp", warp)
        lensing.set("Chroma", 1.0 if (b_chroma.get() and warp > 0.0) else 0.0)
        lensing.set("DiskOn", 1.0 if b_disk.get() else 0.0)
        lensing.set("EchoOn", 1.0 if b_echo.get() else 0.0)
        lensing.set("RingOn", 1.0 if b_ring.get() else 0.0)
        lensing.set("RedOn", 1.0 if b_red.get() else 0.0)
        lensing.set("BloomOn", 1.0 if b_bloom.get() else 0.0)
        lensing.set("ShadowOn", 1.0 if b_shadow.get() else 0.0)
        lensing.set("Glow", gain)
        lensing.set("TintIn", inner_c[0], inner_c[1], inner_c[2])
        lensing.set("TintOut", outer_c[0], outer_c[1], outer_c[2])
        lensing.set("Halo", halo[0], halo[1], halo[2])
        lensing.fullscreen(event)
    except Exception as ex:
        note(str(ex))
