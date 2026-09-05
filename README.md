# Minecraft Bedrock Voice Chat Discord 2.0 — V1.7.0

Bot Discord สำหรับ Minecraft Bedrock Voice Chat Connector V1.7.0

## อัปเดต V1.7.0

- Rework `/test` ใหม่: ผู้ใช้ต้องลงทะเบียน Xbox Gamertag ก่อนใช้งาน
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

V1.7.0 ลบระบบ Zone / Part / Room ออกจาก voice architecture แล้ว:

- ลบ HTTP `/zones` และ `/zone/*`
- ลบ Discord `/zone`, `/zones`, `/delzone`, `/zonerange`, `/range`
- ลบ Zone/Room routing และ centroid fallback เก่าฝั่ง Bot
- Minecraft Addon V1.7.0 ใช้ Acoustic Groups จาก Raycast เป็นระบบ proximity เพียงระบบเดียว
- ถ้า `server_data.json` เก่ามีข้อมูล Zone บอตจะสร้าง `server_data.json.before_remove_zones_*.json` ก่อน migration แล้วลบ field `zones`

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
- `/test` — Test botvc สำหรับผู้ใช้ที่ลงทะเบียนแล้ว

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
