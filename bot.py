import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from dotenv import load_dotenv
import os

# Load environment variables from the secret file
load_dotenv(dotenv_path='.secrets/bot-token.env')

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Get the bot token from environment variables
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    update.message.reply_text(f'Hi {user.first_name}! I am your LLM assistant bot. Send me a question and I will answer it!')

def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    update.message.reply_text('Send me a question and press the "Ask LLM" button to get an answer!')

def ask_question(update: Update, context: CallbackContext) -> None:
    """Store the user's question and show the 'Ask LLM' button."""
    user_question = update.message.text
    context.user_data['question'] = user_question
    
    # Create the "Ask LLM" button
    keyboard = [[InlineKeyboardButton("Ask LLM", callback_data='ask_llm')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    update.message.reply_text(f'Your question: "{user_question}"\nPress the button below to get an answer:', reply_markup=reply_markup)

def button_handler(update: Update, context: CallbackContext) -> None:
    """Handle button presses."""
    query = update.callback_query
    query.answer()
    
    if query.data == 'ask_llm':
        user_question = context.user_data.get('question', 'No question provided')
        # In a real implementation, this is where you would call your LLM
        response = f"You asked: {user_question}\n\nThis is where the LLM response would appear."
        query.edit_message_text(text=response)

def main() -> None:
    """Start the bot."""
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        return
    
    # Create the Updater and pass it your bot's token.
    updater = Updater(TOKEN)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Register handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, ask_question))
    dispatcher.add_handler(CallbackQueryHandler(button_handler))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()