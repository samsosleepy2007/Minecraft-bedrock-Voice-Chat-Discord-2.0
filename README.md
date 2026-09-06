# Minecraft Bedrock Voice Chat Discord 2.0 — Bot V1.7.3 / Addon V1.7.2

Discord Bot + Minecraft Bedrock Voice Chat Connector สำหรับระบบ Proximity Voice แบบ Acoustic Groups / Raycast

## อัปเดตล่าสุด — Re-entry Acoustic Fix

### Addon V1.7.2

แก้บั๊กสำคัญของ Acoustic Groups ที่ทำให้ผู้เล่นหรือ `botvc` สามารถแยกกลุ่มเมื่อเดินออกนอกระยะได้ตามปกติ แต่เมื่อเดินกลับเข้าระยะไมค์แล้วไม่ถูก merge กลับเข้ากลุ่มเดิมอีก

สาเหตุเดิมคือ `acousticPreviousGroups` preserve กลุ่มที่แยกเป็น singleton/sub-group แล้ว mark สมาชิกทั้งหมดเป็น assigned ทำให้ไม่มีขั้นตอนใดนำกลุ่มเดิมกลับมาทดลอง join กันอีกครั้ง

V1.7.2 เพิ่ม Group Reconciliation / Merge Pass หลัง preserve + remaining assignment โดยมีเงื่อนไข:

- Rejoin ใช้ Join Range `R` เท่านั้น
- Preserve สมาชิกเดิมยังใช้ Leave Range `R + 2` เพื่อรักษา hysteresis
- กลุ่มที่จะ merge ต้องอยู่ Dimension เดียวกัน
- ตรวจ centroid ของ combined group
- ตรวจ strict cross-pair distance ทุกคู่ระหว่างสองกลุ่ม
- ตรวจ Head/Chest Raycast ผ่าน pair validation เดิม
- merge ซ้ำจน snapshot อยู่ใน stable state
- ไม่ทำ chain clustering แบบ `A -- B -- C` ถ้า cross-pair ไม่ผ่าน
- บันทึก `acousticPreviousGroups` หลัง reconciliation เสร็จแล้ว

ผลที่ต้องได้:

```text
[Player, botvc]
    ↓ เดินออกเกิน R+2
[Player] [botvc]
    ↓ เดินกลับเข้าภายใน R
[Player, botvc]
```

UUID ของ Behavior Pack / Resource Pack เดิมยังคงเดิมเพื่อรองรับการอัปเดต pack เดิม

### Discord Bot V1.7.3

- ปรับ `ensure_bot_voice_connection()` ให้ verify ว่า VoiceClient อยู่ target Voice Channel จริงหลัง connect/move
- `move_to()` ใช้ timeout 30 วินาทีและ log timeout ชัดเจน
- ถ้า Discord รายงาน connected แต่ channel หลัง reconciliation ไม่ตรง target จะ log expected/actual channel ID
- Acoustic group routing ของ `botvc` ยังคงใช้ target ที่คำนวณจาก `acoustic_groups`
- Test fallback ยังคงเป็น connection-only และจะไม่บังคับ `botvc` ตามเจ้าของ Test เมื่ออยู่นอก Minecraft acoustic range
- เพิ่ม `_patch_once()` เพื่อตรวจ hotfix anchors; ถ้า embedded V1.7.0 source เปลี่ยนจน patch ใช้ไม่ได้ Bot จะ fail loudly แทนการรันโดยที่ patch บางส่วนหายเงียบ ๆ

## Regression cases ที่ตรวจสำหรับ Addon V1.7.2

- initial join: ผ่าน
- leave เกิน `R+2`: ผ่าน
- return ภายใน `R` แล้ว merge ใหม่: ผ่าน
- hysteresis ที่ `R+1`: ยังอยู่กลุ่มเดิมถ้ายังไม่เคย split
- หลัง split แล้วอยู่ `R+1`: ยังไม่ rejoin จนกว่าจะกลับเข้า `R`
- 3-player chain clustering: ไม่รวมผิดกลุ่ม
- cross-dimension: ไม่รวม
- blocked raycast: ไม่รวม
- JavaScript syntax (`node --check`): ผ่าน
- JSON pack files parse: ผ่าน

## V1.7.2 Test Voice Fix ที่ยังคงอยู่

- แก้ปัญหา `/test` ที่ Minecraft เสก `botvc` สำเร็จ แต่ Discord Bot ไม่เข้า Voice Channel
- เพิ่มตัวจัดการ VoiceClient โดยตรงสำหรับ Test/Raycast เพื่อรองรับทั้ง connect, move และ stale VoiceClient
- ตรวจ `View Channel` + `Connect` ก่อนพยายามให้บอทเข้า Voice Channel
- เพิ่ม timeout/reconnect ให้การเชื่อมต่อ VoiceClient
- ไม่กลืน exception ของการเชื่อมต่ออีกต่อไป และพิมพ์สาเหตุจริงลง Render log เช่น permission, timeout หรือ Discord voice connection error
- ถ้า acoustic room pool ว่างหรือ `botvc` ยังเป็นกลุ่มเดี่ยว ระบบ Test จะมี fallback target เป็นห้องเสียงของเจ้าของ Test → ห้องเสียงแรกใน Category → Lobby ตามลำดับ
- `/test` ตรวจ `/setup` และตรวจว่ามี Voice Channel ที่บอทมีสิทธิ์ Connect ก่อนเริ่ม Test
- รองรับกรณี VoiceClient เดิมค้าง/หลุด โดย disconnect แล้วสร้าง connection ใหม่
- ใช้ `discord.py[voice]` เพื่อให้ Render ติดตั้งส่วนรองรับ Voice ครบ

## V1.7.0 ที่ยังคงอยู่

- Rework `/test`: ผู้ใช้ต้องลงทะเบียน Xbox Gamertag ก่อนใช้งาน
- `/test` ใช้ Gamertag ที่ลงทะเบียนเพื่อหา Minecraft world/snapshot ที่ผู้เล่นออนไลน์อยู่
- Bot ส่งคำสั่งกลับ Minecraft ผ่าน response ของ `/update_coords`
- Addon เสก Armor Stand ชื่อ `botvc` และ tag `vc:test_bot` ที่ตำแหน่ง/Dimension ของผู้ใช้
- `botvc` เข้าระบบ Range + Centroid + Strict Distance + Raycast เหมือน participant จริง
- Discord Bot VoiceClient จะ connect/move ไปตาม Acoustic Group ที่มี `botvc`
- `/test` ซ้ำโดยเจ้าของ session จะปิด Test Mode, disconnect Bot และสั่งลบ `botvc`
- เพิ่ม command ID + `command_acks` เพื่อป้องกันคำสั่งซ้ำเมื่อเครือข่ายหน่วง
- หนึ่ง Discord Guild มี Test Session ได้หนึ่งชุดในเวลาเดียวกัน
- ถ้า Bot restart แล้วพบ `botvc` ค้าง ระบบจะ queue คำสั่งลบอัตโนมัติ

## ถอดระบบ Legacy

V1.7.x ลบระบบ Zone / Part / Room ออกจาก voice architecture แล้ว:

- ลบ HTTP `/zones` และ `/zone/*`
- ลบ Discord `/zone`, `/zones`, `/delzone`, `/zonerange`, `/range`
- ลบ Zone/Room routing และ centroid fallback เก่าฝั่ง Bot
- Minecraft Addon ใช้ Acoustic Groups จาก Raycast เป็นระบบ proximity เพียงระบบเดียว
- ถ้า `server_data.json` เก่ามีข้อมูล Zone บอตจะสร้าง backup ก่อน migration แล้วลบ field `zones`

## Protocol V3

Minecraft ส่งข้อมูลหลัก:

- `protocol_version: 3`
- `guild_id`
- `world_id`
- `sequence`
- `timestamp`
- `users` พร้อม `dimension`
- `acoustic_groups`
- `calls`
- `command_acks`

Bot ตอบกลับ:

- `ic_map`
- `commands`

## Commands

- `/setup` — ตั้ง Main Voice Category + Lobby
- `/backup` — สำรองข้อมูล Bot
- `/restore` — กู้ข้อมูล Bot
- `/whitelist` — จัดการ whitelist (ผู้ดูแล)
- `/test` — Test `botvc` สำหรับผู้ใช้ที่ลงทะเบียนแล้ว

## Run

```bash
pip install -r requirements.txt
python bot.py
```

Environment variables:

- `DISCORD_TOKEN`
- `DASHBOARD_PASS`
- `PORT`
- `LOG_WEBHOOK_URL` (optional)

> หมายเหตุ: runtime Bot V1.7.3 ใช้ hotfix layer ใน `bot.py` ครอบ source V1.7.0 ที่เก็บแบบ XZ+Base64 เพื่อให้ Render ใช้งาน source เดิมได้โดยไม่ต้องเปลี่ยนโครงสร้าง repository
