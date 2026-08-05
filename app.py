# Tkinter chat from end for the diseasae-symptom agent in diagnosis.py 

import queue
import threading #queue and threading allow something slow to run in backend without freezing front end 

import tkinter as tk #GUI tool
from tkinter import scrolledtext

from diagnosis import chat as chat_with_agent #importing the chat function from the diagnosis.py file (changing the name to avoid confusion)

THREAD_ID = "gui-session"


class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Symptom Checker")
        self.reply_queue = queue.Queue()

        self.transcript = scrolledtext.ScrolledText(root, width=90, height=32, state="disabled", wrap="word")
        self.transcript.pack(padx=8, pady=8, fill="both", expand=True)

        entry_frame = tk.Frame(root)
        entry_frame.pack(padx=8, pady=(0, 8), fill="x")

        self.entry = tk.Entry(entry_frame)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda event: self.send_message())
        self.entry.focus()

        self.send_button = tk.Button(entry_frame, text="Send", command=self.send_message)
        self.send_button.pack(side="left", padx=(6, 0))

        self.append_transcript(
            "System",
            "Describe your symptoms (e.g. \"I have a headache and I keep throwing up\"). "
            "Say 'reset' to start a new conversation.",
        )
        self.root.after(100, self.poll_queue)

    def append_transcript(self, speaker, text):
        self.transcript.configure(state="normal")
        self.transcript.insert(tk.END, f"{speaker}: {text}\n\n")
        self.transcript.configure(state="disabled")
        self.transcript.see(tk.END)

    def send_message(self):
        message = self.entry.get().strip()
        if not message:
            return
        self.entry.delete(0, tk.END)
        self.append_transcript("You", message)

        self.send_button.config(state="disabled")
        self.transcript.configure(state="normal")
        self.transcript.mark_set("thinking_start", tk.END)
        self.transcript.insert(tk.END, "Assistant: …thinking…\n\n")
        self.transcript.configure(state="disabled")
        self.transcript.see(tk.END)

        threading.Thread(target=self.get_reply, args=(message,), daemon=True).start()

    def get_reply(self, message):
        # Runs on a background thread so the agent's (possibly slow) call to
        # the local LLM doesn't freeze the Tkinter window.
        try:
            reply = chat_with_agent(message, thread_id=THREAD_ID)
        except Exception as exc:  # e.g. LM Studio isn't running
            reply = f"Error talking to the model: {exc}"
        self.reply_queue.put(reply)

    def poll_queue(self):
        try:
            reply = self.reply_queue.get_nowait()
        except queue.Empty:
            pass
        else:
            self.transcript.configure(state="normal")
            self.transcript.delete("thinking_start", tk.END)
            self.transcript.configure(state="disabled")
            self.append_transcript("Assistant", reply)
            self.send_button.config(state="normal")
        self.root.after(100, self.poll_queue)


if __name__ == "__main__":
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()
