# BlackHole - маленькие чёрные дыры вокруг игрока.
# Линзирование фона, горизонт событий, фотонное кольцо, аккреционный диск,
# падающая пыль и искры, притяжение сущностей и низкий гул.

import math
import random
import time

MAX = 8  # столько дыр держат массивы шейдера

mod = Module("BlackHole", "Visuals")
mod.setDesc("Чёрные дыры вокруг игрока: линзирование, диск, притяжение, гул")

Info(mod, "Дыры")
m_mode = Mode(mod, "Режим").add("Россыпь").add("Одна большая")
s_count = Slider(mod, "Сколько дыр").min(1).max(6).step(1).set(3)
s_radius = Slider(mod, "Радиус вокруг игрока").min(4).max(40).step(1).set(14).suffix(" бл.")
s_spread = Slider(mod, "Разброс по высоте").min(0).max(10).step(0.5).set(3)
s_size = Slider(mod, "Размер").min(0.1).max(1.5).step(0.05).set(0.4)
s_life = Slider(mod, "Время жизни").min(2).max(30).step(1).set(9).suffix(" с")
s_delay = Slider(mod, "Пауза между рождениями").min(0.1).max(6).step(0.1).set(1.2).suffix(" с")

Info(mod, "Картинка")
s_warp = Slider(mod, "Сила искривления").min(0.2).max(3).step(0.1).set(1.2)
m_quality = Mode(mod, "Качество").add("Красиво").add("Быстро")
b_disk = Checkbox(mod, "Аккреционный диск").set(True)
b_dust = Checkbox(mod, "Падающая пыль").set(True)
b_sparks = Checkbox(mod, "Искры внутрь").set(True)
c_disk = ColorSetting(mod, "Цвет диска").color(255, 170, 80).alpha(False)
c_halo = ColorSetting(mod, "Цвет гало").color(130, 100, 255).alpha(False)

Info(mod, "Притяжение")
b_pull = Checkbox(mod, "Затягивать сущности").set(True)
b_pull_self = Checkbox(mod, "Тянуть и себя").set(False)
s_pull = Slider(mod, "Сила притяжения").min(0.1).max(3).step(0.1).set(1)

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
STATE = {"next": 0.0, "hum": None, "hum_path": "", "hum_bad": False, "vol": 0.0, "no_pull": False}


def note(msg):
    key = str(msg)[:140]
    if key in SEEN:
        return
    SEEN.add(key)
    print("[BlackHole] " + key)


def rgb01(setting, fallback):
    try:
        raw = setting.get().toHex().lstrip("#")
        return (int(raw[0:2], 16) / 255.0, int(raw[2:4], 16) / 255.0, int(raw[4:6], 16) / 255.0)
    except Exception:
        return fallback


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
    step = 0.5
    travelled = 0.8
    best = (ox + dx * travelled, oy + dy * travelled, oz + dz * travelled)
    steps = int(max(reach - 0.8, 0.0) / step)
    for i in range(1, steps + 1):
        t = 0.8 + step * i
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


def active_holes(now):
    out = []
    for hole in HOLES:
        fade = hole_fade(hole, now)
        if fade <= 0.0:
            continue
        x, y, z = hole_pos(hole, now)
        out.append((hole, x, y, z, fade))
    return out


def disk_axes(tilt):
    nx, ny, nz = math.sin(tilt) * 0.5, 1.0, math.cos(tilt) * 0.5
    ln = math.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx / ln, ny / ln, nz / ln
    ax, ay, az = ny, -nx, 0.0
    la = math.sqrt(ax * ax + ay * ay + az * az)
    if la < 1e-6:
        ax, ay, az, la = 1.0, 0.0, 0.0, 1.0
    ax, ay, az = ax / la, ay / la, az / la
    return (ax, ay, az, ny * az - nz * ay, nz * ax - nx * az, nx * ay - ny * ax)


def dust_of(out, hole, x, y, z, now, fade, tint):
    horizon = hole["rs"] * 2.6
    inner = horizon * 1.15
    outer = horizon * 4.4
    ax, ay, az, bx, by, bz = disk_axes(hole["tilt"])
    base = (now - hole["born"]) * 1.1 + hole["spin"]
    for j in range(12):
        ph = (base * 0.35 + j / 12.0) % 1.0
        alpha = 200.0 * fade * math.sin(math.pi * ph)
        if alpha < 6.0:
            continue
        r1 = inner + (outer - inner) * ((1.0 - ph) ** 1.6)
        r2 = r1 + (outer - inner) * 0.05 * (1.0 - ph)
        a1 = base * (1.3 + 1.9 * (1.0 - ph)) + j * 2.399963
        a2 = a1 - (0.18 + 0.25 * (1.0 - ph))
        c1, s1 = math.cos(a1), math.sin(a1)
        c2, s2 = math.cos(a2), math.sin(a2)
        white = (1.0 - ph) ** 2
        out.extend((
            x + (ax * c1 + bx * s1) * r1,
            y + (ay * c1 + by * s1) * r1,
            z + (az * c1 + bz * s1) * r1,
            x + (ax * c2 + bx * s2) * r2,
            y + (ay * c2 + by * s2) * r2,
            z + (az * c2 + bz * s2) * r2,
            (tint[0] + (1.0 - tint[0]) * white) * 255.0,
            (tint[1] + (1.0 - tint[1]) * white) * 255.0,
            (tint[2] + (1.0 - tint[2]) * white) * 255.0,
            alpha,
        ))


def spark_point(hole, x, y, z, j, ph):
    horizon = hole["rs"] * 2.6
    inner = horizon * 0.95
    outer = horizon * 5.5
    k = min(max(ph, 0.0), 1.0)
    rr = inner + (outer - inner) * ((1.0 - k) ** 1.8)
    ang = j * 2.399963 + hole["spin"] + (1.0 - k) * 2.4
    ele = math.sin(j * 1.7 + hole["tilt"]) * 1.15
    ce = math.cos(ele)
    return (x + math.cos(ang) * ce * rr, y + math.sin(ele) * rr, z + math.sin(ang) * ce * rr)


def sparks_of(out, hole, x, y, z, now, fade, halo):
    base = (now - hole["born"]) * 0.55
    for j in range(10):
        ph = (base + j * 0.1) % 1.0
        alpha = 235.0 * fade * math.sin(math.pi * ph)
        if alpha < 6.0:
            continue
        x1, y1, z1 = spark_point(hole, x, y, z, j, ph)
        x2, y2, z2 = spark_point(hole, x, y, z, j, ph - 0.06)
        white = ph ** 2
        out.extend((
            x1, y1, z1, x2, y2, z2,
            (halo[0] + (1.0 - halo[0]) * white) * 255.0,
            (halo[1] + (1.0 - halo[1]) * white) * 255.0,
            (halo[2] + (1.0 - halo[2]) * white) * 255.0,
            alpha,
        ))


def pull_entities(now, me, holes):
    if STATE["no_pull"] or not holes:
        return
    others = b_pull.get()
    myself = b_pull_self.get()
    if not others and not myself:
        return
    strength = s_pull.get()
    try:
        my_id = me.getId()
    except Exception:
        my_id = None
    victims = []
    if others:
        try:
            victims = list(world.entities())
        except Exception as ex:
            note("сущности не читаются: " + str(ex))
            STATE["no_pull"] = True
            return
    elif myself:
        victims = [me]
    seen = 0
    for ent in victims:
        if seen >= 64:
            break
        seen += 1
        try:
            same = my_id is not None and ent.getId() == my_id
        except Exception:
            same = False
        if same and not myself:
            continue
        try:
            ex_, ey_, ez_ = ent.getX(), ent.getY() + 0.9, ent.getZ()
        except Exception:
            continue
        ax = ay = az = 0.0
        for hole, hx, hy, hz, fade in holes:
            dx, dy, dz = hx - ex_, hy - ey_, hz - ez_
            d2 = dx * dx + dy * dy + dz * dz
            reach = hole["rs"] * 22.0
            if d2 > reach * reach or d2 < 0.0004:
                continue
            d = math.sqrt(d2)
            g = min(strength * 0.33 * fade * hole["rs"] / (d2 * 0.35 + 1.0), 0.5)
            ax += dx / d * g
            ay += dy / d * g
            az += dz / d * g
        if ax == 0.0 and ay == 0.0 and az == 0.0:
            continue
        vx, vy, vz = ax, ay, az
        try:
            v = ent.getVelocity()
            vx, vy, vz = v.x + ax, v.y + ay, v.z + az
        except Exception:
            pass
        try:
            ent.setVelocity(vx, vy, vz)
        except Exception as ex:
            note("скорость не задаётся: " + str(ex))
            STATE["no_pull"] = True
            return


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
    for hole, hx, hy, hz, fade in holes:
        dx, dy, dz = hx - mx, hy - my, hz - mz
        d = math.sqrt(dx * dx + dy * dy + dz * dz)
        near = 1.0 - min(d / span, 1.0)
        loud = fade * near * near * min(1.0, hole["rs"] * 1.8)
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
uniform vec3 Tint;
uniform vec3 Halo;

vec2 dirToUv(mat4 vp, vec3 d, vec2 fallback) {
    vec4 c = vp * vec4(d * 16.0, 1.0);
    if (c.w <= 0.0001) return fallback;
    return clamp(c.xy / c.w * 0.5 + 0.5, vec2(0.0015), vec2(0.9985));
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

    mat4 viewProj = inverse(InvViewProj);

    vec3 bend = vec3(0.0);
    vec3 disk = vec3(0.0);
    float lens = 0.0;
    float shadow = 0.0;
    float ring = 0.0;
    float haze = 0.0;

    for (int i = 0; i < 8; i++) {
        if (float(i) >= Count) break;

        vec3 pos = Holes[i].xyz;
        float rs = Holes[i].w;
        float fade = Extra[i].x;
        float spin = Extra[i].y;
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

        float defl = min(Warp * 2.0 * rs / b, 1.5) * fade * visible;
        bend += toward * defl;
        lens += defl;

        float aa = max(dist * 0.006, 0.012);
        float core = 1.0 - smoothstep(horizon - aa, horizon + aa, b);
        shadow = max(shadow, core * fade * visible);

        float rw = max(horizon * 0.13, 0.015);
        float dr = (b - horizon * 1.05) / rw;
        ring += exp(-dr * dr) * fade * visible;

        haze += fade * visible * (horizon * horizon) / (b * b + horizon * horizon * 1.4) * (1.0 - core);

        if (DiskOn > 0.5) {
            vec3 n = normalize(vec3(sin(Extra[i].z) * 0.5, 1.0, cos(Extra[i].z) * 0.5));
            float dn = dot(dir, n);
            if (abs(dn) > 0.002) {
                float t = dot(pos, n) / dn;
                if (t > 0.0 && t < min(sceneDist, 128.0)) {
                    vec3 q = dir * t - pos;
                    float r = length(q);
                    float inner = horizon * 1.25;
                    float outer = horizon * 4.5;
                    float k = (r - inner) / (outer - inner);
                    if (k > 0.0 && k < 1.0) {
                        float band = smoothstep(0.0, 0.12, k) * (1.0 - smoothstep(0.55, 1.0, k));
                        vec3 t1 = normalize(cross(n, vec3(0.0, 0.0, 1.0)));
                        vec3 t2 = cross(n, t1);
                        float ang = atan(dot(q, t2), dot(q, t1));
                        float swirl = 0.55 + 0.45 * sin(ang * 3.0 - spin * 2.4 + k * 14.0);
                        float doppler = 0.45 + 0.55 * (0.5 + 0.5 * sin(ang - spin * 0.6));
                        vec3 hot = mix(Tint, vec3(1.0), pow(1.0 - k, 3.0) * 0.8);
                        disk += hot * band * swirl * doppler * fade * visible * 1.4;
                    }
                }
            }
        }
    }

    vec3 color = background;
    if (lens > 0.0005) {
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

    color = mix(color, vec3(0.0), clamp(shadow, 0.0, 1.0));
    color += Tint * ring * 1.5;
    color += Halo * haze * 0.45;
    color += disk;

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

        holes = active_holes(now)
        pull_entities(now, me, holes)

        goal = hum_wanted(me, holes)
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
        tint = rgb01(c_disk, (1.0, 0.66, 0.31))
        halo = rgb01(c_halo, (0.51, 0.39, 1.0))
        want_dust = b_dust.get()
        want_sparks = b_sparks.get()

        streaks = []
        shown = 0
        for hole, x, y, z, fade in active_holes(now):
            if shown >= MAX:
                break
            lensing.set("Holes[%d]" % shown, x - cx, y - cy, z - cz, hole["rs"])
            lensing.set("Extra[%d]" % shown, fade, hole["spin"] + (now - hole["born"]) * 1.6, hole["tilt"], 0.0)
            shown += 1
            if want_dust:
                dust_of(streaks, hole, x, y, z, now, fade, tint)
            if want_sparks:
                sparks_of(streaks, hole, x, y, z, now, fade, halo)

        if shown == 0:
            return

        if streaks:
            render3d.lines(event, streaks, True, through=False)

        lensing.set("Count", float(shown))
        lensing.set("Warp", s_warp.get())
        lensing.set("Chroma", 1.0 if m_quality.get() == "Красиво" else 0.0)
        lensing.set("DiskOn", 1.0 if b_disk.get() else 0.0)
        lensing.set("Tint", tint[0], tint[1], tint[2])
        lensing.set("Halo", halo[0], halo[1], halo[2])
        lensing.fullscreen(event)
    except Exception as ex:
        note(str(ex))
