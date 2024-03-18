import logging
import os
import asyncio
import sys
import time

from dotenv import load_dotenv
from openai import OpenAI
from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from aiogram.utils.markdown import hbold
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# Bot token can be obtained via https://t.me/BotFather
TOKEN = os.getenv('BOT_TOKEN')
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
assistant_id = os.getenv('ASSISTANT_ID')



# All handlers should be attached to the Router (or Dispatcher)
dp = Dispatcher()

class ThreadID(StatesGroup):
    thread_id = State()


def submit_message(assistant_id, thread, user_message):
    client.beta.threads.messages.create(
        thread_id=thread, role="user", content=user_message
    )
    return client.beta.threads.runs.create(
        thread_id=thread,
        assistant_id=assistant_id,
    )

def wait_on_run(run, thread):
    while run.status == "queued" or run.status == "in_progress":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread,
            run_id=run.id,
        )
        time.sleep(1)
    return run

def get_response(thread):
    return client.beta.threads.messages.list(thread_id=thread, order="desc")

def pretty_print(messages):
    print("# Messages")
    for m in messages:
        if(m.role == "assistant"):
            msg = m.content[0].text.value
            break

    return msg

@dp.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    """
    This handler receives messages with `/start` command
    """
    # Most event objects have aliases for API methods that can be called in events' context
    # For example if you want to answer to incoming message you can use `message.answer(...)` alias
    # and the target chat will be passed to :ref:`aiogram.methods.send_message.SendMessage`
    # method automatically or call API method directly via
    # Bot instance: `bot.send_message(chat_id=message.chat.id, ...)`
    thread = client.beta.threads.create()

    await state.set_state(ThreadID.thread_id)
    await state.update_data(thread_id=thread.id)
    await message.answer(f"Hello, {hbold(message.from_user.full_name)}!")


@dp.message()
async def echo_handler(message: types.Message, state: FSMContext) -> None:
    """
    Handler will forward receive a message back to the sender

    By default, message handler will handle all message types (like a text, photo, sticker etc.)
    """
    try:
        
        data = await state.get_data()

        run = submit_message(os.getenv('ASSISTANT_ID'), data["thread_id"], message.text)
        wait_on_run(run, data["thread_id"])
        messageMy = pretty_print(get_response(data["thread_id"]))
        await message.answer(messageMy)
    except TypeError as e:
        print(e)
        # But not all the types is supported to be copied so need to handle it
        await message.answer("i")


async def main() -> None:
    # Initialize Bot instance with a default parse mode which will be passed to all API calls
    bot = Bot(TOKEN, parse_mode=ParseMode.HTML)
    # And the run events dispatching
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())