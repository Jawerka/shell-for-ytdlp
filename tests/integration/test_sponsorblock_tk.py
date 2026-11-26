"""Real Tk event loop: dialog lifecycle and cancellation, without app config."""
import tkinter as tk
import traceback
from unittest.mock import Mock

import customtkinter as ctk
import pytest

from ui.components.sponsorblock_dialog import SponsorBlockDialog
from tests.integration.test_sponsorblock_local import service, make_download

pytestmark = pytest.mark.integration


@pytest.fixture
def root():
    try:
        window = ctk.CTk()
    except tk.TclError as exc:
        pytest.skip(f'Tk display unavailable: {exc}')
    window.withdraw()
    window.title('QA SponsorBlock lifecycle')
    window.callback_errors = []
    window.report_callback_exception = lambda *args: window.callback_errors.append(''.join(traceback.format_exception(*args)))
    yield window
    window.destroy()
    assert not window.callback_errors


def pump(root, milliseconds=350):
    root.after(milliseconds, root.quit)
    root.mainloop()


@pytest.mark.parametrize('decision,remember', [
    ('bypass', True), ('bypass', False), ('retry', False), ('cancel', True),
])
def test_real_tk_answer_once_and_no_leftover_poll(root, decision, remember):
    response = Mock()
    dialog = SponsorBlockDialog(root, response, lambda: False)
    assert not dialog.remember.get()
    dialog.remember.set(remember)
    pump(root)
    timer = dialog._poll_id
    dialog.answer(decision)
    dialog.answer(decision)  # double click cannot release a second answer
    assert not dialog.winfo_exists()
    assert timer not in root.tk.call('after', 'info')
    response.assert_called_once_with((decision, remember))
    pump(root)


def test_real_tk_closed_window_means_cancel(root):
    response = Mock()
    dialog = SponsorBlockDialog(root, response, lambda: False)
    pump(root)
    root.tk.eval(dialog.protocol('WM_DELETE_WINDOW'))
    response.assert_called_once_with(('cancel', False))
    assert not dialog.winfo_exists()
    pump(root)


def test_real_tk_cancel_while_parent_hidden(root):
    response = Mock()
    cancelled = [False]
    dialog = SponsorBlockDialog(root, response, lambda: cancelled[0])
    pump(root)
    assert dialog.state() == 'withdrawn'
    cancelled[0] = True
    pump(root)
    response.assert_called_once_with(('cancel', False))
    assert not dialog.winfo_exists()


def test_real_tk_button_click_animation_has_no_callback_after_close(root, capsys):
    response = Mock()
    dialog = SponsorBlockDialog(root, response, lambda: False)
    pump(root)
    row = dialog.winfo_children()[-1]
    button = next(child for child in row.winfo_children() if isinstance(child, ctk.CTkButton))
    button._clicked()  # Include CTk's delayed click animation, unlike invoke().
    pump(root)
    response.assert_called_once_with(('bypass', False))
    captured = capsys.readouterr()
    assert 'invalid command name' not in captured.err
    assert 'bad window path name' not in captured.err


def test_real_tk_modal_and_escape(root):
    response = Mock()
    pump(root)  # CTk finishes its delayed Windows titlebar initialization.
    root.deiconify()
    pump(root)
    dialog = SponsorBlockDialog(root, response, lambda: False)
    pump(root)
    assert dialog.grab_current() is dialog, (root.state(), dialog.state(), dialog.winfo_viewable(), dialog._poll_id)
    # Invoke the Tk binding itself (not answer()) to verify Escape semantics.
    # event_generate delivers to the actual focused dialog in the Tk loop.
    dialog.event_generate('<Escape>')
    pump(root)
    response.assert_called_once_with(('cancel', False))
    assert not dialog.winfo_exists()
    assert root.grab_current() is None


@pytest.mark.parametrize('decision,remember', [('bypass', True), ('bypass', False), ('cancel', True)])
def test_real_process_and_tk_question_together(root, make_download, service, monkeypatch, decision, remember):
    """The actual worker, Tk question, HTTP error and yt-dlp restart in one run."""
    import threading
    from pathlib import Path
    from ui.main_window import MainWindow

    make, config, state = make_download
    root.config_manager = config
    root._cancel_event = threading.Event()
    root._sponsorblock_state = state
    root.sound_manager = Mock()
    root.log_viewer = Mock()
    root.progress_bar = Mock()
    root.downloader = None
    instances = []

    def factory(config, log, progress, **kwargs):
        dl, commands = make('gui flow')
        dl.log_callback = log
        dl.progress_callback = progress
        dl.sponsorblock_question = kwargs['sponsorblock_question']
        dl.sponsorblock_notice = kwargs['sponsorblock_notice']
        instances.append((dl, commands))
        return dl

    monkeypatch.setattr('ui.main_window.YouTubeDownloader', factory)
    pump(root)
    root.deiconify()
    pump(root)
    outcome = []
    done = threading.Event()

    def work():
        try:
            outcome.append(MainWindow._download_thread(root, 'https://www.youtube.com/watch?v=test1234567'))
        except Exception as exc:
            outcome.append(exc)
        finally:
            done.set()

    answers = []

    def drive():
        for dialog in root.winfo_children():
            if isinstance(dialog, SponsorBlockDialog) and dialog._ready and not dialog.answered:
                assert '/media.mp4' not in service['requests']
                dialog.remember.set(remember)
                answers.append(decision)
                dialog.answer(decision)
        if done.is_set():
            root.quit()
        else:
            root.after(25, drive)

    worker = threading.Thread(target=work, daemon=True)
    worker.start()
    deadline = root.after(12000, root.quit)
    root.after(25, drive)
    try:
        root.mainloop()
        assert done.is_set(), 'Worker hung while processing the SponsorBlock answer'
    finally:
        root.after_cancel(deadline)
        if not done.is_set():
            root._cancel_event.set()
            if root.downloader:
                root.downloader.cancel()
        worker.join(timeout=3)
    assert outcome == [decision == 'bypass']
    assert answers == [decision]
    root.sound_manager.play_attention.assert_called_once()
    dl, commands = instances[0]
    assert len(commands) == (2 if decision == 'bypass' else 1)
    assert config.get('SPONSORBLOCK_FAILURE_POLICY') == ('bypass' if decision == 'bypass' and remember else 'ask')
    files = list(Path(config.get('DOWNLOAD_PATH')).glob('*.mp4'))
    assert bool(files) == (decision == 'bypass')
    assert root._cancel_event.is_set() == (decision == 'cancel')
    pump(root)  # No callbacks to a destroyed question or lingering modal grab.
    assert root.grab_current() is None
