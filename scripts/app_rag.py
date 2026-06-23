import gradio as gr

from lore_master.rag_chat.rag_chain import build_rag_chain

chain = build_rag_chain()

theme = gr.themes.Soft(font=["Inter", "system-ui", "sans-serif"])


def chat(message: str, history: list[dict]) -> str:
    return chain.invoke({"question": message, "history": history})


demo = gr.ChatInterface(
    fn=chat, title="Hollow Knight Lore Bot (RAG, LangChain)"
)

if __name__ == "__main__":
    demo.launch(share=True, theme=theme)
