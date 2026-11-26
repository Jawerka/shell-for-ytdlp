"""Неблокирующий для Tk вопрос: рабочий поток получает ответ через callback."""
import customtkinter as ctk
import tkinter as tk
import logging

logger = logging.getLogger('UI-for-ytdlp.sponsorblock_dialog')


class SponsorBlockDialog(ctk.CTkToplevel):
    def __init__(self, parent, on_answer, cancelled):
        self._ready = False
        self._closing = False
        self._after_ids = set()
        self._poll_id = None
        super().__init__(parent)
        self.withdraw()
        self.title('SponsorBlock не отвечает')
        self.geometry('550x310')
        self.resizable(False, False)
        self.on_answer = on_answer
        self.cancelled = cancelled
        self.answered = False
        self.parent = parent
        ctk.CTkLabel(self, text='SponsorBlock не отвечает', font=ctk.CTkFont(size=18, weight='bold')).pack(pady=(20, 10))
        ctk.CTkLabel(self, text=(
            'Не удалось получить отметки рекламных вставок.\n'
            'Можно продолжить скачивание, но спонсорские\n'
            'вставки останутся в видео.'), justify='left').pack(padx=20, pady=10)
        self.remember = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(self, text=(
            'При следующих сбоях продолжать автоматически.\n'
            'После восстановления снова вырезать вставки.'),
            variable=self.remember).pack(padx=20, pady=15)
        row = ctk.CTkFrame(self, fg_color='transparent')
        row.pack(pady=10)
        for text, decision in (
            ('Скачать без вырезания', 'bypass'),
            ('Проверить снова', 'retry'), ('Отменить', 'cancel'),
        ):
            ctk.CTkButton(row, text=text, width=110,
                          command=lambda value=decision: self.answer(value)).pack(side='left', padx=4)
        self.protocol('WM_DELETE_WINDOW', lambda: self.answer('cancel'))
        self.bind('<Escape>', lambda event: self.answer('cancel'))
        self._ready = True
        self._poll()

    def answer(self, decision):
        if not self._ready or self.answered:
            return
        self.answered = True
        try:
            self.on_answer((decision, bool(self.remember.get())))
        finally:
            self.destroy()

    def iconbitmap(self, *args, **kwargs):
        # В некоторых установках CTk отсутствует стандартная иконка;
        # её отложенная загрузка не должна давать исключение Tk callback.
        try:
            return super().iconbitmap(*args, **kwargs)
        except tk.TclError:
            logger.debug('Иконка окна SponsorBlock недоступна', exc_info=True)

    def destroy(self):
        if self._closing:
            return
        self._closing = True
        # CTk тоже планирует отложенную настройку заголовка/иконки.
        # Быстрый ответ не должен оставлять обращения к уничтоженному окну.
        for timer in tuple(self._after_ids):
            self.after_cancel(timer)
        self._poll_id = None
        super().destroy()

    def after(self, ms, func=None, *args):
        if func is None:
            return super().after(ms)
        timer = None

        def run():
            self._after_ids.discard(timer)
            if not self._closing:
                func(*args)

        timer = super().after(ms, run)
        self._after_ids.add(timer)
        return timer

    def after_cancel(self, timer):
        self._after_ids.discard(timer)
        return super().after_cancel(timer)

    def _poll(self):
        self._poll_id = None
        if self.cancelled():
            self.answer('cancel')
            return
        if self.parent.state() == 'normal' and self.state() == 'withdrawn':
            self.transient(self.parent)
            self.deiconify()
            self.grab_set()
            self.focus_set()
        self._poll_id = self.after(150, self._poll)
