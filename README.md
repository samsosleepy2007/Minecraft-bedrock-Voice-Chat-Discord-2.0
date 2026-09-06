# Minecraft Bedrock Voice Chat Discord 2.0 — Bot V1.7.3 / Addon V1.7.3

Discord Bot + Minecraft Bedrock Voice Chat Connector สำหรับระบบ Proximity Voice แบบ Acoustic Groups / Raycast

## อัปเดตล่าสุด — Addon V1.7.3 Symmetric Occlusion Fix

แก้บั๊กกรณีผู้เล่น A/B อยู่ใน Acoustic Group เดียวกัน แล้ว A เข้าไปในห้องและปิดประตู แต่ระบบยัง preserve `[A,B]` ต่อไปจนกว่าจะมีคนออกนอกระยะก่อน

พฤติกรรมเดิมเกิดจาก Raycast มีโอกาสให้ผลต่างกันตามทิศทางของคู่ผู้เล่น:

```text
Preserve existing group: B → A
Rejoin / merge:          A → B
```

V1.7.2 ใช้ `maxDistance = len - 0.25` ทำให้ blocker ที่อยู่ชิดปลาย ray เช่นประตูที่ปิดอยู่ใกล้ผู้เล่นปลายทางสามารถหลุดออกจากช่วงตรวจได้ในทิศทางหนึ่ง แต่ถูกตรวจเจอในอีกทิศทางหนึ่ง

### สิ่งที่เปลี่ยนใน V1.7.3

- `acousticRayClear()` ใช้ symmetric segment test
- ตรวจ Head A→B และ B→A
- ตรวจ Chest A→B และ B→A
- acoustic segment หนึ่งระดับจะถือว่า clear ก็ต่อเมื่อ ray ทั้งสองทิศทาง clear
- ยังคงกติกาหลัก `Head clear OR Chest clear`
- ลด endpoint trim จาก `0.25` block เหลือ epsilon `0.02` block
- กำแพง/ประตูที่ block ray จะตัด existing acoustic connection ได้ทันที
- hysteresis ยังคงใช้เฉพาะเรื่องระยะ: Join `R`, Leave `R + 2`
- ไม่เพิ่ม special-case สำหรับ Door; geometry เดียวกันยังใช้กับ Wall / Glass / Trapdoor / Slab / Fence และสิ่งกีดขวางอื่น
- รักษา UUID เดิมของ Behavior Pack และ Resource Pack
- bump `header.version`, `modules[].version` และชื่อ pack เป็น `1.7.3`

### Regression ใหม่

ทดสอบโดยไม่ขยับตำแหน่ง A/B และจำลอง blocker ที่อยู่ชิด endpoint ของ ray:

```text
Door open   -> [A,B]
Door closed -> [A] [B]
Door open   -> [A,B]
Door closed -> [A] [B]
```

ตรวจ regression ของ logic เก่าพบว่า blocker แบบเดียวกันสามารถให้:

```text
old B→A = clear
old A→B = blocked
```

ขณะที่ V1.7.3 ให้ blocked เหมือนกันทั้ง A→B และ B→A

ไฟล์ patch ที่ใช้กับ Addon V1.7.2 อยู่ที่:

```text
addon-patches/v1.7.3-symmetric-raycast.patch
```

SHA-256 ของ package V1.7.3 ที่ build/test:

```text
0b343a68c43337ae35da7a98791b9cd8a97cd809b755ea54ebca53b536aefb9a
```

> Discord Bot ไม่ต้องเปลี่ยน version ในรอบนี้ เพราะ root cause อยู่ฝั่ง Minecraft acoustic raycast; Bot คงอยู่ที่ V1.7.3

## Addon V1.7.2 — Re-entry Acoustic Fix ที่ยังคงอยู่

V1.7.2 แก้บั๊ก Acoustic Groups ที่แยกกลุ่มเมื่อเดินออกนอกระยะได้ แต่เมื่อเดินกลับเข้าระยะแล้ว singleton/sub-group ที่ preserve ไว้ไม่ถูก merge กลับ

V1.7.2 เพิ่ม Group Reconciliation / Merge Pass หลัง preserve + remaining assignment โดยมีเงื่อนไข:

- Rejoin ใช้ Join Range `R`
- Preserve สมาชิกเดิมใช้ Leave Range `R + 2`
- กลุ่มที่จะ merge ต้องอยู่ Dimension เดียวกัน
- ตรวจ centroid ของ combined group
- ตรวจ strict cross-pair distance ทุกคู่ระหว่างสองกลุ่ม
- ตรวจ Head/Chest Raycast ผ่าน pair validation
- merge ซ้ำจน snapshot อยู่ใน stable state
- ไม่ทำ chain clustering แบบ `A -- B -- C` ถ้า cross-pair ไม่ผ่าน
- บันทึก `acousticPreviousGroups` หลัง reconciliation เสร็จแล้ว

ผลที่ต้องได้:

```text
[Player, botvc]
    ↓ เดินออกเกิน R+2
[Player] [botvc]
    ↓ เดินกลับเข้าภายใน R และ Raycast clear
[Player, botvc]
```

## Discord Bot V1.7.3

- `ensure_bot_voice_connection()` verify ว่า VoiceClient อยู่ target Voice Channel จริงหลัง connect/move
- `move_to()` ใช้ timeout 30 วินาทีและ log timeout
- ถ้า connected แต่ channel ไม่ตรง target จะ log expected/actual channel ID
- Acoustic group routing ของ `botvc` ใช้ target จาก `acoustic_groups`
- Test fallback เป็น connection-only และไม่บังคับ `botvc` ตามเจ้าของ Test เมื่ออยู่นอก Minecraft acoustic range
- `_patch_once()` ตรวจ hotfix anchors เพื่อไม่ให้ patch fail แบบเงียบ ๆ

## Test Voice Fix ที่ยังคงอยู่

- `/test` ใช้ registered Xbox Gamertag
- Bot ส่ง `spawn_test_bot` ผ่าน response ของ `/update_coords`
- Addon เสก Armor Stand ชื่อ `botvc` พร้อม tag `vc:test_bot`
- `botvc` เข้า Range + Centroid + Strict Distance + Raycast เหมือน participant จริง
- Discord Bot VoiceClient connect/move ตาม Acoustic Group ของ `botvc`
- `/test` ซ้ำโดยเจ้าของ session จะปิด Test Mode, disconnect Bot และสั่งลบ `botvc`
- command ID + `command_acks` ป้องกันคำสั่งซ้ำเมื่อเครือข่ายหน่วง
- หนึ่ง Discord Guild มี Test Session ได้หนึ่งชุด
- stale `botvc` cleanup หลัง Bot restart

## ถอดระบบ Legacy

V1.7.x ลบระบบ Zone / Part / Room ออกจาก voice architecture แล้ว:

- ไม่มี HTTP `/zones` และ `/zone/*`
- ไม่มี Discord `/zone`, `/zones`, `/delzone`, `/zonerange`, `/range`
- ไม่มี Zone/Room routing หรือ centroid fallback เก่า
- Minecraft Addon ใช้ Acoustic Groups จาก Raycast เป็นระบบ proximity หลัก

## Protocol V3

Minecraft ส่ง:

- `protocol_version: 3`
- `guild_id`
- `world_id`
- `sequence`
- `timestamp`
- `users` พร้อม `dimension`
- `range`
- `acoustic_groups`
- `calls`
- `command_acks`

Bot ตอบ:

- `ic_map`
- `commands`

## Commands

- `/setup` — ตั้ง Main Voice Category + Lobby
- `/backup` — สำรองข้อมูล Bot
- `/restore` — กู้ข้อมูล Bot
- `/whitelist` — จัดการ whitelist
- `/test` — Test `botvc` สำหรับผู้ใช้ที่ลงทะเบียนแล้ว

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

> runtime Bot V1.7.3 ใช้ hotfix layer ใน `bot.py` ครอบ source V1.7.0 ที่เก็บแบบ XZ+Base64 เพื่อให้ Render ใช้งาน source เดิมได้โดยไม่เปลี่ยนโครงสร้าง repository
