"""
Language Translation Tool - CodeAlpha Internship Task 1
Uses Google Translate API with a simple tkinter GUI
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import html
import requests
from deep_translator.exceptions import RequestError, TooManyRequests

# using deep-translator since googletrans can be flaky sometimes
from deep_translator import GoogleTranslator

# list of commonly used languages (didn't want to dump ALL of them)
LANGUAGES = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Italian": "it",
    "Portuguese": "pt",
    "Russian": "ru",
    "Japanese": "ja",
    "Korean": "ko",
    "Chinese (Simplified)": "zh-CN",
    "Arabic": "ar",
    "Hindi": "hi",
    "Turkish": "tr",
    "Dutch": "nl",
    "Swedish": "sv",
    "Polish": "pl",
    "Thai": "th",
    "Vietnamese": "vi",
    "Indonesian": "id",
    "Greek": "el",
    "Czech": "cs",
    "Romanian": "ro",
    "Hungarian": "hu",
    "Ukrainian": "uk",
    "Bengali": "bn",
    "Urdu": "ur",
}


class TranslatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Language Translator")
        self.root.geometry("750x520")
        self.root.resizable(False, False)
        self.root.configure(bg="#f0f0f0")

        self.setup_ui()

    def setup_ui(self):
        # title label at the top
        title = tk.Label(
            self.root, text="Language Translation Tool",
            font=("Helvetica", 16, "bold"), bg="#f0f0f0"
        )
        title.pack(pady=10)

        # frame for language selection dropdowns
        lang_frame = tk.Frame(self.root, bg="#f0f0f0")
        lang_frame.pack(pady=5)

        tk.Label(lang_frame, text="From:", font=("Arial", 11), bg="#f0f0f0").grid(
            row=0, column=0, padx=10
        )
        self.source_lang = ttk.Combobox(
            lang_frame, values=list(LANGUAGES.keys()),
            state="readonly", width=22
        )
        self.source_lang.set("English")
        self.source_lang.grid(row=0, column=1, padx=5)

        # swap button
        swap_btn = tk.Button(
            lang_frame, text="⇄", font=("Arial", 14),
            command=self.swap_languages, relief="flat", bg="#f0f0f0"
        )
        swap_btn.grid(row=0, column=2, padx=8)

        tk.Label(lang_frame, text="To:", font=("Arial", 11), bg="#f0f0f0").grid(
            row=0, column=3, padx=10
        )
        self.target_lang = ttk.Combobox(
            lang_frame, values=list(LANGUAGES.keys()),
            state="readonly", width=22
        )
        self.target_lang.set("Spanish")
        self.target_lang.grid(row=0, column=4, padx=5)

        # text areas - input and output side by side
        text_frame = tk.Frame(self.root, bg="#f0f0f0")
        text_frame.pack(pady=10, padx=15, fill="both", expand=True)

        # input text
        input_label = tk.Label(
            text_frame, text="Enter text:", font=("Arial", 10), bg="#f0f0f0"
        )
        input_label.grid(row=0, column=0, sticky="w", padx=5)

        self.input_text = tk.Text(
            text_frame, height=12, width=38, font=("Arial", 11),
            wrap="word", relief="solid", borderwidth=1
        )
        self.input_text.grid(row=1, column=0, padx=5, pady=3)

        # output text
        output_label = tk.Label(
            text_frame, text="Translation:", font=("Arial", 10), bg="#f0f0f0"
        )
        output_label.grid(row=0, column=1, sticky="w", padx=5)

        self.output_text = tk.Text(
            text_frame, height=12, width=38, font=("Arial", 11),
            wrap="word", relief="solid", borderwidth=1, state="disabled",
            bg="#fafafa"
        )
        self.output_text.grid(row=1, column=1, padx=5, pady=3)

        # buttons at the bottom
        btn_frame = tk.Frame(self.root, bg="#f0f0f0")
        btn_frame.pack(pady=8)

        self.translate_btn = tk.Button(
            btn_frame, text="Translate", font=("Arial", 12, "bold"),
            bg="#4285f4", fg="white", padx=20, pady=5,
            command=self.do_translate, relief="raised", cursor="hand2"
        )
        self.translate_btn.grid(row=0, column=0, padx=10)

        copy_btn = tk.Button(
            btn_frame, text="Copy Result", font=("Arial", 11),
            bg="#34a853", fg="white", padx=15, pady=5,
            command=self.copy_to_clipboard, relief="raised", cursor="hand2"
        )
        copy_btn.grid(row=0, column=1, padx=10)

        clear_btn = tk.Button(
            btn_frame, text="Clear", font=("Arial", 11),
            bg="#ea4335", fg="white", padx=15, pady=5,
            command=self.clear_all, relief="raised", cursor="hand2"
        )
        clear_btn.grid(row=0, column=2, padx=10)

        # status bar for feedback
        self.status_var = tk.StringVar(value="Ready")
        status_bar = tk.Label(
            self.root, textvariable=self.status_var,
            font=("Arial", 9), bg="#e0e0e0", anchor="w", relief="sunken"
        )
        status_bar.pack(side="bottom", fill="x")

    def swap_languages(self):
        """swap source and target langs"""
        src = self.source_lang.get()
        tgt = self.target_lang.get()
        self.source_lang.set(tgt)
        self.target_lang.set(src)

    def do_translate(self):
        """handle translate button click - runs in a thread so UI doesnt freeze"""
        text = self.input_text.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("Oops", "Please enter some text to translate!")
            return

        src_code = LANGUAGES.get(self.source_lang.get(), "en")
        tgt_code = LANGUAGES.get(self.target_lang.get(), "es")

        if src_code == tgt_code:
            messagebox.showinfo("Note", "Source and target languages are the same.")
            return

        self.translate_btn.config(state="disabled")
        self.status_var.set("Translating...")

        # do the translation in background thread to keep ui responsive
        thread = threading.Thread(
            target=self.translate_text, args=(text, src_code, tgt_code)
        )
        thread.daemon = True
        thread.start()

    def translate_text(self, text, src, tgt):
        """actual translation logic"""
        try:
            translator = GoogleTranslator(source=src, target=tgt)
            result = translator.translate(text)

            if not result:
                raise RuntimeError("The translation service returned an empty response. Please try again.")

            # update UI from the main thread
            self.root.after(0, self.show_result, result)
        except (TooManyRequests, RequestError, requests.exceptions.RequestException) as google_error:
            # Google Translate's unofficial web endpoint can throttle requests.
            # Try MyMemory's documented public API before reporting a failure.
            try:
                result = self.translate_with_mymemory(text, src, tgt)
                self.root.after(0, self.show_result, result)
            except Exception as fallback_error:
                self.root.after(
                    0, self.show_error,
                    "Google Translate could not complete the request, and the backup service also failed. "
                    f"Google: {google_error}. Backup: {fallback_error}",
                )
        except Exception as e:
            self.root.after(0, self.show_error, str(e))

    @staticmethod
    def translate_with_mymemory(text, src, tgt):
        """Fallback provider, split into requests under MyMemory's 500-byte limit."""
        chunks = []
        current = ""
        for char in text:
            if len((current + char).encode("utf-8")) > 450:
                chunks.append(current)
                current = ""
            current += char
        if current:
            chunks.append(current)

        translated_chunks = []
        for chunk in chunks:
            response = requests.get(
                "https://api.mymemory.translated.net/get",
                params={"q": chunk, "langpair": f"{src}|{tgt}", "mt": "1"},
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()
            if str(data.get("responseStatus")) != "200":
                raise RuntimeError(data.get("responseDetails") or "MyMemory returned an error.")
            translated = data.get("responseData", {}).get("translatedText", "")
            if not translated:
                raise RuntimeError("MyMemory returned an empty translation.")
            translated_chunks.append(html.unescape(translated))
        return "".join(translated_chunks)

    def show_result(self, translated):
        """display the translated text"""
        self.output_text.config(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", translated)
        self.output_text.config(state="disabled")
        self.translate_btn.config(state="normal")
        self.status_var.set("Translation complete!")

    def show_error(self, error_msg):
        """show error if something goes wrong"""
        messagebox.showerror("Translation Error", f"Something went wrong:\n{error_msg}")
        self.translate_btn.config(state="normal")
        self.status_var.set("Error occurred")

    def copy_to_clipboard(self):
        """copy translated text to clipboard"""
        self.output_text.config(state="normal")
        result = self.output_text.get("1.0", "end").strip()
        self.output_text.config(state="disabled")

        if result:
            self.root.clipboard_clear()
            self.root.clipboard_append(result)
            self.status_var.set("Copied to clipboard!")
        else:
            messagebox.showinfo("Nothing to copy", "Translate something first.")

    def clear_all(self):
        """clear both text fields"""
        self.input_text.delete("1.0", "end")
        self.output_text.config(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.config(state="disabled")
        self.status_var.set("Ready")


if __name__ == "__main__":
    root = tk.Tk()
    app = TranslatorApp(root)
    root.mainloop()
