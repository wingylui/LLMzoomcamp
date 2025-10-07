import streamlit as st
import time
import uuid
import random
from rag import hybrid_description_rag
from minitor import conversion_tracking, feedback_tracking

# 🧁 App Header
st.title("BakeBuddy – Your Smart Recipe Chat")
st.write("Ask me for any baking recipe, and I’ll find or create one for you. Whether it’s chewy cookies, soft bread, or a rich chocolate cake — I’ll tailor the recipe to your ingredients and preferences.")
st.caption("💡 Friendly reminder: Please don’t share personal or sensitive information here — just your baking ideas and questions! Let’s keep the chat all about the treats. 🧁")

# 🗨️ Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Ready to whip up something sweet?"}]
    
if "feedback_list" not in st.session_state:
    st.session_state.feedback_list = []

# 💬 Display previous chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 🧠 Accept user input
if question := st.chat_input("What would you like to bake today?"):
    # Store user input
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    # Generate assistant response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        with st.spinner("🍰 Mixing ideas in the kitchen..."):
            id_ = str(uuid.uuid4())
            response = hybrid_description_rag(question)
            answer = response["answer"]

            # store the question and answer
            conversion_tracking(conversation_id= id_, answer_js = response)


        # Simulate streaming with preserved newlines
        for chunk in answer.split(" "):  # split only by spaces, not newlines
            full_response += chunk + " "
            time.sleep(0.03)
            # replace \n with actual Markdown line breaks
            formatted_response = full_response.replace("\n", "  \n")
            message_placeholder.markdown(formatted_response + "▌")
        # Final render
        message_placeholder.markdown(full_response.replace("\n", "  \n"))

    # Save to history
    st.session_state.messages.append({"role": "assistant", "content": full_response})


    # Randomly ask for feedback (~10% chance)
    if random.random() < 0.1:
        st.markdown("### 📝 Did you find this recipe helpful?")
        feedback = st.radio(
            "Your feedback:",
            options=["👍 Helpful", "👎 Not helpful", "🤔 Neutral"],
            key=f"feedback_{id_}"  # unique key for each feedback widget
        )
        if feedback:
            st.session_state.feedback_list.append({
                "conversation_id": id_,
                "question": question,
                "answer": formatted_response,
                "feedback": feedback
            })
            feedback_tracking(
                conversation_id=id_,
                feedback=feedback
            )
            st.success("Thanks for your feedback! 🎉")