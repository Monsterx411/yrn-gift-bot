from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import logging

from bot.config import config
from database.repository import (
    get_user_by_id, get_active_templates, get_template_by_id,
    create_template, update_template, delete_template,
    get_dashboard_stats, log_admin_action, set_admin, get_or_create_user
)
from database.models import CardTemplate
from database.engine import get_session
from utils.keyboards import admin_keyboard, back_keyboard
from utils.formatters import format_admin_dashboard

logger = logging.getLogger(__name__)


def admin_required(func):
    """Decorator to restrict access to admins."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in config.ADMIN_IDS:
            await update.effective_message.reply_text("⛔ Unauthorized. This command is for admins only.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Open the admin panel."""
    user_id = update.effective_user.id
    if user_id not in config.ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized.")
        return

    # Ensure admin flag in DB
    async with get_session() as session:
        user = await get_or_create_user(
            session,
            telegram_id=user_id,
            username=update.effective_user.username,
            first_name=update.effective_user.first_name,
        )
        user.is_admin = True
        await session.commit()

    await update.message.reply_text(
        "*🛠️ Admin Panel*",
        parse_mode="Markdown",
        reply_markup=admin_keyboard()
    )


async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin panel callbacks."""
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = update.effective_user.id

    if user_id not in config.ADMIN_IDS:
        await query.edit_message_text("⛔ Unauthorized.")
        return

    if data == "admin_dashboard":
        async with get_session() as session:
            stats = await get_dashboard_stats(session)
            await log_admin_action(session, user_id, "viewed_dashboard")
            await session.commit()

        text = format_admin_dashboard(stats)
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=admin_keyboard())

    elif data == "admin_templates":
        async with get_session() as session:
            # Get all templates including inactive
            from sqlalchemy import select
            result = await session.execute(select(CardTemplate).order_by(CardTemplate.key))
            templates = result.scalars().all()

        if not templates:
            await query.edit_message_text("No templates found.", reply_markup=admin_keyboard())
            return

        text = "*📝 Card Templates*\n\n"
        keyboard = []
        for tmpl in templates:
            status = "✅" if tmpl.is_active else "🚫"
            text += f"{status} `{tmpl.key}` — *{tmpl.name}* — `${tmpl.amount/100:.2f}` — {tmpl.price_stars}⭐\n"
            keyboard.append([
                InlineKeyboardButton(
                    f"{status} {tmpl.key} (${tmpl.amount/100:.2f})",
                    callback_data=f"adm_tmpl_{tmpl.id}"
                )
            ])

        keyboard.append([InlineKeyboardButton("➕ New Template", callback_data="adm_new_template")])
        keyboard.append([InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_dashboard")])

        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("adm_tmpl_"):
        tmpl_id = int(data[9:])
        async with get_session() as session:
            tmpl = await get_template_by_id(session, tmpl_id)

        if not tmpl:
            await query.edit_message_text("Template not found.", reply_markup=admin_keyboard())
            return

        text = (
            f"*Template: {tmpl.key}*\n\n"
            f"Name: `{tmpl.name}`\n"
            f"Description: {tmpl.description or 'N/A'}\n"
            f"Amount: `${tmpl.amount/100:.2f}`\n"
            f"Currency: `{tmpl.currency}`\n"
            f"Color: `{tmpl.color}`\n"
            f"Stars Cost: `{tmpl.price_stars}⭐`\n"
            f"Active: `{'Yes' if tmpl.is_active else 'No'}`\n"
            f"Created: `{tmpl.created_at.strftime('%Y-%m-%d')}`"
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ Toggle Active", callback_data=f"adm_toggle_{tmpl.id}"),
                InlineKeyboardButton("✏️ Edit", callback_data=f"adm_edit_{tmpl.id}"),
            ],
            [InlineKeyboardButton("🗑️ Delete", callback_data=f"adm_delete_{tmpl.id}")],
            [InlineKeyboardButton("🔙 Templates", callback_data="admin_templates")],
        ]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("adm_toggle_"):
        tmpl_id = int(data[11:])
        async with get_session() as session:
            tmpl = await get_template_by_id(session, tmpl_id)
            if tmpl:
                tmpl.is_active = not tmpl.is_active
                await log_admin_action(
                    session, user_id, "toggled_template",
                    {"template_id": tmpl_id, "active": tmpl.is_active}
                )
                await session.commit()
                await query.edit_message_text(
                    f"✅ Template `{tmpl.key}` is now **{'active' if tmpl.is_active else 'inactive'}**.",
                    parse_mode="Markdown",
                    reply_markup=admin_keyboard()
                )

    elif data.startswith("adm_delete_"):
        tmpl_id = int(data[10:])
        async with get_session() as session:
            deleted = await delete_template(session, tmpl_id)
            await log_admin_action(session, user_id, "deleted_template", {"template_id": tmpl_id})
            await session.commit()
            status = "✅ Deleted." if deleted else "❌ Not found."
            await query.edit_message_text(status, reply_markup=admin_keyboard())

    elif data == "adm_new_template":
        # Prompt admin to send template data
        context.user_data["awaiting_template"] = True
        await query.edit_message_text(
            "📝 *Create New Template*\n\n"
            "Send template data in this format:\n\n"
            "`key|Name|Description|Amount in cents|Currency|Color hex|Stars cost`\n\n"
            "Example:\n"
            "`gold|Gold Card|$200 Gold Card|20000|USD|#FFA500|180`\n\n"
            "_Or send /cancel to abort._",
            parse_mode="Markdown"
        )

    elif data == "admin_users":
        async with get_session() as session:
            from sqlalchemy import select, func
            result = await session.execute(
                select(CardTemplate)
            )
            # Simple stat
        async with get_session() as session:
            from database.models import User
            result = await session.execute(
                select(User).order_by(User.created_at.desc()).limit(10)
            )
            users = result.scalars().all()

        text = "*👥 Recent Users (last 10)*\n\n"
        for u in users:
            text += (
                f"`{u.telegram_id}` — "
                f"{u.first_name or 'Unknown'} "
                f"{'👑' if u.is_admin else ''}\n"
            )
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=admin_keyboard())


async def handle_template_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin input for creating a new template."""
    if not context.user_data.get("awaiting_template"):
        return

    user_id = update.effective_user.id
    if user_id not in config.ADMIN_IDS:
        return

    text = update.message.text.strip()

    if text.lower() == "/cancel":
        context.user_data["awaiting_template"] = False
        await update.message.reply_text("Cancelled.", reply_markup=admin_keyboard())
        return

    parts = text.split("|")
    if len(parts) < 6:
        await update.message.reply_text(
            "❌ Invalid format. Use:\n"
            "`key|Name|Description|Amount in cents|Currency|Color hex|Stars cost`\n\n"
            "Example: `gold|Gold Card|$200 Gold Card|20000|USD|#FFA500|180`"
        )
        return

    try:
        data = {
            "key": parts[0].strip(),
            "name": parts[1].strip(),
            "description": parts[2].strip() if len(parts) > 2 else "",
            "amount": int(parts[3].strip()),
            "currency": parts[4].strip().upper() if len(parts) > 4 else "USD",
            "color": parts[5].strip() if len(parts) > 5 else "#4CAF50",
            "price_stars": int(parts[6].strip()) if len(parts) > 6 else 0,
            "is_active": True,
        }
    except (IndexError, ValueError) as e:
        await update.message.reply_text(f"❌ Parse error: {e}. Please try again.")
        return

    async with get_session() as session:
        tmpl = await create_template(session, data)
        await log_admin_action(session, user_id, "created_template", data)
        await session.commit()

    context.user_data["awaiting_template"] = False
    await update.message.reply_text(
        f"✅ Template `{tmpl.key}` created! (`${tmpl.amount/100:.2f}`)",
        parse_mode="Markdown",
        reply_markup=admin_keyboard()
    )


def register(application):
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^admin_|^adm_"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_template_input))