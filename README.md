# Minecraft Bedrock Voice Chat Discord 2.0

Discord Bot สำหรับระบบ Proximity Voice ของ Minecraft Bedrock โดยทำงานร่วมกับ Bedrock Addon ผ่าน HTTP API แล้วจัดผู้เล่นเข้า Discord Voice Channel ตามกลุ่มเสียงที่ Addon คำนวณมา

## เวอร์ชันปัจจุบัน

**Bot V1.6.4 — Raycast Voice + Phone System Update**

> Addon ที่ใช้งานคู่กันควรเป็น V1.6.4 เพื่อใช้ protocol v2 / acoustic groups แบบใหม่ได้ครบถ้วน

## อัปเดต / แก้ไขใน V1.6.4

### ระบบ Voice / Raycast

- เพิ่มการรองรับ `protocol_version: 2`
- รับ `acoustic_groups` ที่ Minecraft Addon คำนวณจาก **Range + Group Centroid + Strict Pair Distance + Player-to-Player Raycast**
- Bot ไม่ต้องคำนวณ geometry หรือกำแพงของโลก Minecraft เองเมื่อใช้ protocol v2
- รองรับข้อมูล `dimension` เพื่อไม่ให้ผู้เล่นคนละ Dimension ถูกจัด proximity group ร่วมกัน
- เพิ่ม `guild_id`, `world_id`, `sequence` และ `timestamp` ใน snapshot รุ่นใหม่
- แยก runtime state ตาม **Discord Guild + Minecraft World** เพื่อลดปัญหา snapshot ของอีกโลกเขียนทับกัน
- ปฏิเสธ/หลีกเลี่ยง snapshot เก่าที่ลำดับไม่ถูกต้อง
- Phone Call / Group Call ยังมี priority สูงกว่า Raycast proximity
- รักษา `call-room-fix` และการจอง Voice Channel สำหรับผู้เล่นที่กำลังโทร
- Zone / Part / Room เดิมยังคงอยู่เป็น **Legacy/Fallback** สำหรับ payload รุ่นเก่าในช่วงเปลี่ยนระบบ

### ความเสถียรของ Bot

- แก้ลำดับการโหลดข้อมูลที่เดิมสามารถเรียก `load_data()` ก่อน helper ของ zone range พร้อมใช้งาน
- เพิ่ม runtime lock/state สำหรับการประมวลผล snapshot แยกแต่ละ world
- ยังคงรองรับ IC Name map ที่ส่งกลับ Minecraft
- ยังคงรองรับ server mute / server deafen จากสถานะไมค์และหูฟังใน Addon

### การเปลี่ยนแปลงฝั่ง Addon ที่ทำงานคู่กับ Bot V1.6.4

- Proximity Voice หลักเปลี่ยนจาก Zone/Room ไปเป็น **Raycast Acoustic Groups**
- ใช้ Group Centroid เป็น candidate/broad-phase และตรวจระยะจริงระหว่างสมาชิกทุกคนก่อนรวมกลุ่ม
- ใช้ Raycast ระหว่างผู้เล่นเพื่อกันเสียงเมื่อมีกำแพง/สิ่งกีดขวาง
- เพิ่ม Join/Leave hysteresis เพื่อลดการสลับ Discord Voice Channel ที่ขอบระยะ
- เพิ่ม Dimension เข้า voice snapshot
- ผู้เล่นจะไม่ถูกสุ่มเบอร์โทรให้อัตโนมัติเมื่อเข้าเซิร์ฟเวอร์
- ใช้โทรศัพท์ครั้งแรกจะให้เลือกเบอร์เอง **4 หลัก ตัวเลขเท่านั้น**
- `0000` สงวนไว้สำหรับ `botvc`
- เพิ่ม Phone Number Registry ระดับโลกเพื่อป้องกันเลขซ้ำ แม้เจ้าของเลขออฟไลน์
- กรอกเบอร์ตัวเองผิด/ไม่ครบ/เกิน/ไม่ใช่ตัวเลข/ซ้ำ จะให้กรอกใหม่
- เวลาโทรหรือส่งข้อความ หากกรอกเบอร์ปลายทางผิดหรือว่าง จะกลับหน้า Home ของโทรศัพท์แทนการเปิดฟอร์มเดิมวนซ้ำ เพื่อแก้ UX โดยเฉพาะบน iPhone

## โครงสร้าง

```text
.
├── bot.py                    # entrypoint สำหรับ Render / Python
├── bot_source.py.xz.b64      # source V1.6.4 แบบ lossless XZ + Base64
├── requirements.txt
└── templates/
    └── dashboard.html
```

`bot.py` จะถอด `bot_source.py.xz.b64` กลับเป็น source Python V1.6.4 ในหน่วยความจำแล้วรันทันที ดังนั้นคำสั่งบน Render ยังคงเป็น `python bot.py` ตามเดิม การเก็บ source แบบ payload นี้ใช้เพื่อเลี่ยงข้อจำกัดขนาดไฟล์ของตัวเชื่อม GitHub ที่ใช้ในการอัปโหลดครั้งนี้ โดย source ต้นฉบับก่อนบีบอัดมี SHA-256:

```text
5392808e358032a0872fbd9cbc8246f15528e41cf6555b0243f9e6f27dd6cb3d
```

## Environment Variables

ตั้งค่าบน Render หรือระบบโฮสต์ที่ใช้:

```text
DISCORD_TOKEN=Discord bot token
DASHBOARD_PASS=Dashboard password
PORT=8080
```

`LOG_WEBHOOK_URL` เป็น optional ตามโค้ดปัจจุบัน

> ควรกำหนด `DASHBOARD_PASS` เองใน environment และไม่ใช้ค่า default สำหรับ production

## ติดตั้ง

```bash
pip install -r requirements.txt
python bot.py
```

Dependencies หลัก:

- discord.py
- aiohttp
- jinja2
- PyNaCl

## การใช้งานร่วมกับ Minecraft

Bot เปิด HTTP server ด้วย `aiohttp` และรับ snapshot จาก Minecraft Bedrock Dedicated Server / Addon ผ่าน endpoint `/update_coords` จากนั้นจัด Discord Voice Channel ตามสถานะ proximity/call

สำหรับระบบ Raycast แบบใหม่ ให้ใช้ Addon V1.6.4 ที่ส่ง protocol v2 และ `acoustic_groups`

## หมายเหตุ

- ระบบเสียงจริงยังส่งผ่าน Discord Voice ไม่ได้ส่ง audio microphone ผ่าน Minecraft
- Raycast และการตรวจ block ทำที่ฝั่ง Minecraft Addon ส่วน Bot มีหน้าที่จัดกลุ่ม Discord Voice Channel ตามผลที่ได้รับ
- Zone/Part/Room ยังถูกเก็บไว้ใน V1.6.4 เพื่อ compatibility/fallback และมีแผนถอด legacy voice logic หลังระบบ Raycast ผ่านการทดสอบจริง
