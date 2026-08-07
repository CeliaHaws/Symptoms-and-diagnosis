# Tkinter chat from end for the diseasae-symptom agent in diagnosis.py

import sys
sys.dont_write_bytecode = True #stop __pycache__ from being generated when this runs

import queue
import threading #queue and threading allow something slow to run in backend without freezing front end
from matplotlib.lines import Line2D #fr building the

import tkinter as tk #GUI tool
from tkinter import scrolledtext

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg #embeds a matplotlib figure inside a Tkinter widget
from matplotlib.figure import Figure
from diagnosis import chat as chat_with_agent #importing the chat function from the diagnosis.py file (changing the name to avoid confusion)
from diagnosis import chat as chat_with_agent, DiagnosisVisuliser, engine as diagnosis_engine #importing the chat function, the graph panel, and the shared engine


THREAD_ID = "gui-session" #the interface


class ChatApp: #bundles all the sections together into a class so that it can be run as a single object
    def __init__(self, root): # setting up the window
        self.root = root #the window things are being built insiide
        self.root.title("Symptom Checker")
        self.reply_queue = queue.Queue() #creating an empty queue to hold the replies from the agent

        main = tk.Frame(root) #splits the window into a chat side and a graph side
        main.pack(fill="both", expand=True)
        chat_frame = tk.Frame(main)
        chat_frame.pack(side="left", fill="both", expand=True)
        graph_frame = tk.Frame(main)
        graph_frame.pack(side="right", fill="both", expand=True)


        self.transcript = scrolledtext.ScrolledText(chat_frame, width=90, height=32, state="disabled", wrap="word")
        self.transcript.pack(padx=8, pady=8, fill="both", expand=True)
         #creates a place where the conversation will be displayed, with a scrollbar

        entry_frame = tk.Frame(chat_frame)
        entry_frame.pack(padx=8, pady=(0, 8), fill="x")
        # box that hold. the typing line and send button

        self.entry = tk.Entry(entry_frame)
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda event: self.send_message())
        self.entry.focus()
        # the box where the user types their message, and binds the "Enter" key to send the message

        self.send_button = tk.Button(entry_frame, text="Send", command=self.send_message) #commans=self (this bit causes it to send when clicked)
        self.send_button.pack(side="left", padx=(6, 0))
            # the button that sends the message when clicked

        self.visualiser = DiagnosisVisuliser(diagnosis_engine) #tracks which symptoms have been said and colours the graph accordingly
        self.message_count = 0 #counts how many messages the user has sent, so the graph button unlocks after the 2nd

        graph_controls = tk.Frame(graph_frame)
        graph_controls.pack(fill="x", padx=8, pady=(6, 6))
        self.generate_graph_button = tk.Button(
            graph_controls, text="Generate Graph", command=self.generate_graph, state="disabled"
        )
        self.generate_graph_button.pack(side="left")
        # the graph is only drawn when this button is pressed, not on every message -
        # redrawing the layout is slow, so we don't want it happening on every send

        self.figure = Figure(figsize=(6, 6), dpi=150)
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=graph_frame)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.visualiser.redraw(ax=self.ax) #draw the graph once at startup, before anything's been said
        self.canvas.draw()

        self.append_transcript(
            "System",
            "Describe your symptoms (e.g. \"I have a headache and I keep throwing up\"). "
            "Say 'reset' to start a new conversation.",
        )
        self.root.after(100, self.poll_queue)

    def append_transcript(self, speaker, text):# adding conversation to the transcript box
        self.transcript.configure(state="normal")
        self.transcript.insert(tk.END, f"{speaker}: {text}\n\n")
        self.transcript.configure(state="disabled")
        self.transcript.see(tk.END)

    def send_message(self): # after hitting the send message
        message = self.entry.get().strip()
        if not message: #if empty dont do anything
            return
        self.entry.delete(0, tk.END) # reading the input
        self.append_transcript("You", message) # putting your messsage into the transcript box

        threading.Thread(target=self.visualiser.record_input, args=(message,), daemon=True).start()
        #records the newly reported symptoms on its own thread, completely separate from the chat -
        #the canonicaliser/graph work never blocks sending a message or starting the LLM reply

        self.message_count += 1
        if self.message_count >= 2:
            self.generate_graph_button.config(state="normal") #unlock the graph button after the 2nd prompt

        self.send_button.config(state="disabled") # when the clicked cant click again until the reply is received
        self.transcript.configure(state="normal")
        self.transcript.mark_set("thinking_start", tk.END) #invisible bookmark?
        self.transcript.insert(tk.END, "Assistant: …thinking…\n\n")
        self.transcript.configure(state="disabled")
        self.transcript.see(tk.END)

        threading.Thread(target=self.get_reply, args=(message,), daemon=True).start() #asking the agent the information in the background separetly so that the front end doesnt freeze

    def generate_graph(self): # redraws the graph on demand, instead of on every message
        self.visualiser.redraw(ax=self.ax)
        self.canvas.draw()

    def get_reply(self, message): #asking the AI the chat input
        # Runs on a background thread so the agent's (possibly slow) call to
        # the local LLM doesn't freeze the Tkinter window.
        try:
            reply = chat_with_agent(message, thread_id=THREAD_ID) # shows if there is an error
        except Exception as exc:  # e.g. LM Studio isn't running
            reply = f"Error talking to the model: {exc}"
        self.reply_queue.put(reply) # putting the answer from the LLM into the queue so that it can be displayed in the front end

    def poll_queue(self): # check if the AI has finished answering yet, and if so, update the screen
        try:
            reply = self.reply_queue.get_nowait() #sees if anything in queue is nothing throws an error if there anything in the queue doesnt spend too long there if nothing in there so doesnt freeze
        except queue.Empty: #as in try error thrown if empty this just makes it pass thorugh if theres an error
            pass
        else: # if somthing in the queue
            self.transcript.configure(state="normal")
            self.transcript.delete("thinking_start", tk.END) #stop the thinking as there is a reply
            self.transcript.configure(state="disabled")
            self.append_transcript("Assistant", reply)
            self.send_button.config(state="normal")
        self.root.after(100, self.poll_queue) # keeps checking the queue every 100 milliseconds to see if there is a reply from the agent, and if so, it displays it in the transcript box and re-enables the send button.


if __name__ == "__main__": #keeping the window open
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()
