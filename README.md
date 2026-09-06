# Minecraft Bedrock Voice Chat Discord 2.0 — Bot V1.7.5 / Addon V1.7.6

Discord Bot + Minecraft Bedrock Voice Chat Connector สำหรับระบบ Proximity Voice แบบ Acoustic Groups / Raycast

## V1.7.6 — Enclosed Room + Hit-Face Parallel Barrier

V1.7.6 แก้ regression ของ Addon V1.7.5 ที่กำแพงจริงขนาด 6×6 สามารถถูกตีความว่าเล็กเกิน Mic Range แล้วปล่อยให้ผู้เล่นเชื่อม Voice กันได้

สาเหตุหลักที่แก้:

1. V1.7.5 เดาแกนความกว้างของกำแพงจากทิศ A↔B ทำให้การยิงเฉียงมีโอกาสวัด “ความหนา” ของกำแพงแทน “ความกว้าง”.
2. short cell probe ของ V1.7.5 เริ่มใกล้/ภายใน collision volume ของ block ที่กำลังตรวจ จึงไม่ควรใช้เป็นตัวตัดสิน span ของกำแพง.

V1.7.6 เปลี่ยนเป็น `BlockRaycastHit.face` + parallel acoustic rays และเพิ่มระบบตรวจห้องปิดสนิท.

## กฎ Acoustic Barrier ใหม่

สิ่งกีดขวางทั่วไปยังใช้:

```text
BLOCK เมื่อ
width >= ceil(Mic Range)
AND
height >= ceil(Mic Range)
```

ตัวอย่าง Range = `5`:

| Barrier | ผล |
| --- | --- |
| 1 × 2 | เชื่อม |
| 4 × 5 | เชื่อม |
| 5 × 3 | เชื่อม |
| 5 × 4 | เชื่อม |
| 5 × 5 | กันเสียง |
| 6 × 6 | กันเสียง |

แต่ถ้าเป็น **ห้องปิดสนิท** จะใช้กฎพิเศษ:

```text
A อยู่ใน sealed acoustic component
B อยู่นอก component เดียวกัน
→ BLOCK เสมอ
```

ดังนั้นห้องขนาดเล็กกว่า Mic Range ก็ยังกันเสียง ถ้าปิดรอบด้านจริงทั้งผนัง + หลังคา + พื้น.

## Hit-Face Parallel Barrier Scan

V1.7.6 ใช้หน้าของ block ที่ Ray ชนจริง:

```text
East / West -> normal X, width Z
North / South -> normal Z, width X
```

จากนั้นเลื่อน A↔B ray แบบขนานไปตามแกนความกว้างและแกน Y เพื่อวัด span ของ barrier.

parallel ray จะนับเป็น barrier เดียวกันเฉพาะเมื่อ first hit อยู่บน wall-normal coordinate เดียวกับ anchor hit จึงไม่เอาสิ่งกีดขวางอื่นที่อยู่ไกลกว่าไปเพิ่มความกว้างโดยผิดพลาด.

ผลคือกำแพง 6×6 ยังคงถูกอ่านว่าใหญ่พอแม้ A/B จะยืนเฉียงกับกำแพง.

## Enclosed Room Detection

ห้องปิดสนิทตรวจเฉพาะเมื่อ Head และ Chest direct paths ถูกบังทั้งคู่ เพื่อลด overhead.

ระบบใช้:

- 2D acoustic flood-fill ที่ระดับอกของผู้เล่น
- collision-aware one-block transitions ด้วย `getBlockFromRay(... includePassableBlocks:false)`
- search radius = `ceil(Range) + 1`
- safety node budget สูงสุด 4096
- ถ้า flood-fill ออกถึง boundary -> ไม่ถือว่าปิด
- ถ้าคอลัมน์ใดไม่มีหลังคาหรือพื้นภายใน bounded vertical search -> ไม่ถือว่าปิด
- per-snapshot enclosure cache + transition cache

เหตุผลที่ใช้ 2D + vertical closure แทน 3D flood-fill เต็มก้อนคือควบคุม cost ให้ใกล้ O(R²) แทน O(R³).

ห้องใหญ่ที่เกิน bounded enclosure search ยังมีกฎ Barrier Width/Height เป็น fallback อยู่ จึงเน้น Enclosed Room Detection ไปที่เคสสำคัญคือ “ห้องเล็กกว่าระยะ แต่ปิดสนิท”.

## `/test` Realtime Barrier Diagnostics

Performance Counter ใน Action Bar ของผู้เล่นทุกคนยังคงทำงานเมื่อ `/test` active และมี `botvc`.

V1.7.6 เพิ่ม debug barrier เช่น:

```text
B:ENC BLOCK
B:W W5+ H5+ BLOCK
B:E W5+ H3 PASS
```

ตัวอย่างเต็ม:

```text
VC TEST PERF 3ms (avg 2.4 / max 5)
| Tick 6.0% | P8 G3 Pair18 Ray31 Wall6 Enc2 Cache4
| Dcfg5.0 Bot5.0 Pend0
| B:ENC BLOCK
```

Counter ใหม่:

- `parallel_rays`
- `enclosure_checks`
- `enclosure_cache_hits`
- `enclosure_transition_cache_hits`
- `enclosure_nodes`
- `enclosure_rays`
- `enclosure_vertical_rays`
- `enclosure_blocks`

V1.7.5 `barrier_cell_cache_hits` / `barrier_probe_rays` ถูกถอด เพราะ inside-block cell probe classifier ไม่ใช้อีกแล้ว.

## Regression V1.7.6

Mock geometry regression โดยใช้ helper logic ของ V1.7.6:

```text
Range 5 + wall 5×3                  -> PASS
Range 5 + wall 5×4                  -> PASS
Range 5 + wall 5×5                  -> BLOCK
Range 5 + wall 6×6                  -> BLOCK
Range 5 + wall 6×6 diagonal         -> BLOCK
small sealed room vs outside        -> BLOCK / ENC BLOCK
open door aligned with A/B          -> PASS
same sealed room + small pillar     -> PASS
tiny sealed room smaller than R     -> BLOCK / ENC BLOCK
tiny roofless room smaller than R   -> PASS
```

Package/static validation:

- JavaScript `node --check`: ผ่าน
- JSON parse: 18 files ผ่าน
- ZIP CRC/integrity: ผ่าน
- package entries: 81
- Behavior Pack / Resource Pack version: `[1,7,6]`
- UUID เดิมยังคงเดิม

SHA-256 ของ Addon V1.7.6:

```text
9cfed40403f4ce7b0e6f6a6a0d566e2fc387bb30332186c64978cb308c2ad6e3
```

Implementation notes ใน repository:

```text
addon-patches/v1.7.6-enclosed-room-parallel-barrier.md
```

> Mock/static tests ยังไม่แทน BDS geometry จริง ควรทดสอบ Door, Trapdoor, Slab, Fence, Glass, wall edge/corner และห้องเปิดหลังคาบน server จริงด้วย `/test` diagnostics.

## Bot V1.7.5 — Desired-State Move Delay

Bot ยังเป็น V1.7.5 เพราะรอบ V1.7.6 แก้เฉพาะ Minecraft acoustic geometry.

`move_delay` หมายถึงเวลาที่ desired Discord Voice target ต้องนิ่งก่อนย้าย ไม่ใช่ cooldown หลังการย้ายครั้งก่อน.

```text
t=0.0 target Room2 -> start timer
t=1.0 target ยัง Room2 -> timer เดินต่อ
t=5.0 เมื่อ delay=5.0 -> MOVE
```

ถ้า target เปลี่ยนก่อนครบเวลา pending เก่าจะถูกยกเลิก.

กฎ:

- `0.0` -> move ใน allocator decision แรก
- `0.1–5.0` -> target ต้องนิ่งครบเวลาที่ตั้ง
- same target snapshot ไม่ reset timer
- target เปลี่ยน -> cancel pending เก่า
- per-member pending state
- legacy `MOVE_COOLDOWN = 3.0` ปิดแล้ว
- ไม่ move ซ้ำเมื่อ Discord state ตรง target

`/test` Action Bar ยังแสดง:

```text
Dcfg5.0 Bot5.0 Pend1:2.7s
```

## Voice Move Delay Setting

Addon UI:

```text
0.0 – 5.0 seconds
step = 0.1
default/recommended = 3.0
```

ค่าต่ำกว่า `3.0` มีหน้าคำเตือนและให้ยืนยันหรือคืนค่าเดิม.

Dynamic Property:

```text
vc:move_delay
```

Protocol V3 optional field:

```json
{
  "move_delay": 3.0
}
```

Bot invalid / missing value fallback เป็น `3.0`.

## Version History

### Addon V1.7.6

- sealed room always blocks outside participants
- hit-face-aware wall orientation
- parallel acoustic span rays
- fixes 6×6 wall false-pass regression
- `/test` barrier/enclosure diagnostics

### V1.7.5

- acoustic-blocking barrier span attempt
- Bot desired-state move-delay debounce
- configured/applied/pending delay diagnostics

### V1.7.4

- range-scaled Barrier Span
- Voice Move Delay UI `0–5`
- realtime `/test` Performance Counter

### V1.7.3

- symmetric Head/Chest A→B + B→A raycast
- endpoint epsilon `0.02`
- closed blocker can split an existing group immediately

### V1.7.2

- acoustic group re-entry reconciliation / merge pass
- Join `R`, Leave `R+2`
- strict pair + centroid + no chain clustering

## Test Voice System

- `/test` ใช้ registered Xbox Gamertag
- Bot ส่ง `spawn_test_bot` ผ่าน `/update_coords`
- Addon เสก Armor Stand `botvc` พร้อม tag `vc:test_bot`
- `botvc` เข้า Acoustic Group เหมือน participant จริง
- Discord Bot VoiceClient connect/move ตาม Acoustic Group ของ `botvc`
- `/test` ซ้ำโดย owner ปิด Test, disconnect Bot และลบ `botvc`
- command ID + `command_acks` ป้องกัน command ซ้ำ
- stale `botvc` cleanup หลัง Bot restart

## Architecture

Minecraft Acoustic Groups เป็น source of truth ของ proximity. Discord Bot นำ desired groups ไปจัด Voice Channel โดย Phone Call / Group Call มี priority เหนือ proximity.

Legacy Zone / Part / Room ไม่ใช่ dependency ของ proximity ใน V1.7.x.

## Commands

- `/setup` — ตั้ง Main Voice Category + Lobby
- `/backup` — สำรองข้อมูล Bot
- `/restore` — กู้ข้อมูล Bot
- `/whitelist` — จัดการ whitelist
- `/test` — Test `botvc` + realtime performance / delay / barrier diagnostics

## Run Bot

```bash
pip install -r requirements.txt
python bot.py
```

Environment variables:

- `DISCORD_TOKEN`
- `DASHBOARD_PASS`
- `PORT`
- `LOG_WEBHOOK_URL` (optional)

Bot runtime ใช้ hotfix layer ใน `bot.py` ครอบ lossless V1.7.0 source ที่เก็บใน `bot_source.py.xz.b64`.