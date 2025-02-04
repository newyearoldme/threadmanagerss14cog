import discord
from discord.ext import commands
from datetime import datetime

if "cogs" in __name__:
    from .utils.crud import log_thread_closure, get_thread_logs, was_thread_closed, init_db
else:
    from utils.crud import log_thread_closure, get_thread_logs, was_thread_closed, init_db


class PaginatedView(discord.ui.View):
    def __init__(self, embeds: list[discord.Embed]):
        super().__init__()
        self.embeds = embeds
        self.current_page = 0
        self.message: discord.WebhookMessage | None = None
        self.update_buttons()

    def update_buttons(self):
        """Обновляет состояние кнопок в зависимости от текущей страницы"""
        self.first_page.disabled = self.current_page == 0
        self.previous_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page == len(self.embeds) - 1
        self.last_page.disabled = self.current_page == len(self.embeds) - 1

    async def on_timeout(self):
        """Прекращает работу после таймаута"""
        for button in self.children:
            button.disabled = True
        try:
            if self.message:
                await self.message.edit(view=self)
        except discord.NotFound:
            pass

    @discord.ui.button(label="⏪", style=discord.ButtonStyle.secondary)
    async def first_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.current_page = 0
        self.update_buttons()
        await self.update_embed(interaction)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
    async def previous_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.current_page = max(0, self.current_page - 1)
        self.update_buttons()
        await self.update_embed(interaction)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.current_page = min(len(self.embeds) - 1, self.current_page + 1)
        self.update_buttons()
        await self.update_embed(interaction)

    @discord.ui.button(label="⏩", style=discord.ButtonStyle.secondary)
    async def last_page(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.current_page = len(self.embeds) - 1
        self.update_buttons()
        await self.update_embed(interaction)

    @discord.ui.button(label="❌", style=discord.ButtonStyle.red)
    async def stop(self, button: discord.ui.Button, interaction: discord.Interaction):
        """Останавливает пагинацию (удаляет сообщение)"""
        if self.message:
            try:
                await self.message.delete()
            except discord.NotFound:
                pass
            self.message = None
        self.clear_items()

    async def update_embed(self, interaction: discord.Interaction):
        """Обновляет текущий Embed и состояние кнопок"""
        if self.message:
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

    async def send(self, ctx):
        """Отправляет первое сообщение и активирует пагинацию"""
        self.update_buttons()
        self.message = await ctx.respond(embed=self.embeds[self.current_page], view=self)


class ThreadManagerCog(commands.Cog):
    def __init__(self, client):
        self.client = client
        init_db()

    async def _close_thread(self, ctx: discord.ApplicationContext, expected_channel_name: str):
        if not isinstance(ctx.channel, discord.Thread):
            await ctx.respond("❌ Эта команда работает только в жалобах или обжалованиях", ephemeral=True)
            return

        thread = ctx.channel

        # Проверка: была ли ветка уже закрыта
        if was_thread_closed(thread.id):
            await ctx.respond("❌ Эта тема уже была закрыта ранее", ephemeral=True)
            return

        parent_channel = thread.parent
        if not parent_channel or parent_channel.name.lower() != expected_channel_name.lower():
            await ctx.respond(f"❌ Эта команда предназначена только для канала {expected_channel_name}", ephemeral=True)
            return

        # Логируем закрытие ветки
        log_thread_closure(
            user_id=ctx.author.id,
            thread_id=thread.id,
            channel_id=parent_channel.id,
        )

        # Закрываем ветку
        self.close_mapping = {
            "📑┇жалобы": {
                "noun": "Жалоба",
                "verb": "закрыта"
            },
            "📑┇обжалования": {
                "noun": "Обжалование",
                "verb": "закрыто"
            }
        }

        mapping_entry = self.close_mapping.get(expected_channel_name.lower(), {"noun": "Ветка", "verb": "закрыта"})
        noun_text = mapping_entry["noun"]
        verb_text = mapping_entry["verb"]

        await ctx.respond(f"✅ {noun_text} {thread.name} успешно {verb_text}")
        await thread.edit(archived=True, locked=True)

    @commands.slash_command(name="close_complaint", description="Закрыть жалобу")
    async def close_complaint(self, ctx: discord.ApplicationContext):
        """Закрыть ветку в жалобах"""
        await self._close_thread(ctx, "📑┇жалобы")

    @commands.slash_command(name="close_appeal", description="Закрыть обжалование")
    async def close_appeal(self, ctx: discord.ApplicationContext):
        """Закрыть ветку в обжалованиях"""
        await self._close_thread(ctx, "📑┇обжалования")

    @commands.slash_command(name="complaints_stats", description="Показать статистику по закрытым жалобам или обжалованиям")
    async def complaints_stats(
        self,
        ctx: discord.ApplicationContext,
        user: discord.Member,
        channel: str = discord.Option(
            description="Выберите канал",
            choices=["📑┇жалобы", "📑┇обжалования"],
        ),
        start_date: str = discord.Option(
            description="Введите начальную дату в формате YYYY-MM-DD (например, 2025-01-01), часовой пояс utc",
            default=None,
        ),
        end_date: str = discord.Option(
            description="Введите конечную дату в формате YYYY-MM-DD (например, 2025-01-31), часовой пояс utc",
            default=None,
        )
    ):
        # Проверка, что канал корректный
        allowed_channels = ["📑┇жалобы", "📑┇обжалования"]
        if channel not in allowed_channels:
            await ctx.respond(f"❌ Канал '{channel}' недопустим. Выберите из: {', '.join(allowed_channels)}.", ephemeral=True)
            return

        # Поиск канала по имени
        guild_channel = discord.utils.get(ctx.guild.channels, name=channel)
        if not guild_channel or not isinstance(guild_channel, discord.ForumChannel):
            await ctx.respond(f"❌ Канал '{channel}' не найден или не является форумным.", ephemeral=True)
            return

        # Преобразование строковых дат в datetime (если они заданы)
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
        except ValueError:
            await ctx.respond("❌ Неверный формат даты. Используйте формат YYYY-MM-DD.", ephemeral=True)
            return

        if start_date_obj and end_date_obj and end_date_obj < start_date_obj:
            await ctx.respond(
                f"❌ Конечная дата ({end_date_obj.strftime('%Y-%m-%d')}) не может быть раньше начальной даты ({start_date_obj.strftime('%Y-%m-%d')}).",
                ephemeral=True,
            )
            return

        # Получение логов через CRUD
        logs = get_thread_logs(user_id=user.id, channel_id=guild_channel.id)

        # Фильтрация по датам
        if start_date_obj:
            logs = [log for log in logs if log.closed_at >= start_date_obj]
        if end_date_obj:
            logs = [log for log in logs if log.closed_at <= end_date_obj]

        mapping = {
            "жалобы": "жалоб",
            "обжалования": "обжалований"
        }
        normalized_channel = channel.split("┇")[-1].strip().lower()
        channel_type = mapping.get(normalized_channel)

        if not logs:
            await ctx.respond(
                f"У {user.mention} нет закрытых {channel_type} в указанный период",
                ephemeral=True,
            )
            return

        # Создание embed для пагинации
        embeds = []
        for i in range(0, len(logs), 5):
            log_page = logs[i:i + 5]

            embed = discord.Embed(
                title = f"Статистика закрытых {channel_type} для {user.display_name}",
                color=discord.Color.blue(),
            )

            for log_item in log_page:
                thread_url = f"https://discord.com/channels/{ctx.guild.id}/{log_item.thread_id}"
                embed.add_field(
                    name=f"Тема: {thread_url}",
                    value=f"Закрыта: {log_item.closed_at.strftime('%Y-%m-%d %H:%M')}",
                    inline=False,
                )
            embed.set_footer(text=f"Общее количество: {len(logs)}")
            embeds.append(embed)

        # Отправка через PaginatedView
        view = PaginatedView(embeds)
        await view.send(ctx)


def setup(client):
    client.add_cog(ThreadManagerCog(client))
