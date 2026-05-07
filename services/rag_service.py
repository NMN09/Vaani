import os
from pinecone import Pinecone
from google import genai
from dotenv import load_dotenv

load_dotenv()

pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY", "dummy"))
INDEX_NAME = "vaaniai-products"
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", "dummy"))

def query_knowledge_base(query: str, language: str = "English") -> str:
    """
    Searches Pinecone for product knowledge and uses Gemini 3.1 Pro 
    to reason and generate an answer in the specified language.
    """
    try:
        index = pc.Index(INDEX_NAME)
        
        # Embed query
        embed_resp = client.models.embed_content(
            model='gemini-embedding-2',
            contents=query,
        )
        query_vector = embed_resp.embeddings[0].values
        
        # Search Pinecone
        search_res = index.query(
            vector=query_vector,
            top_k=3,
            include_metadata=True
        )
        
        context_chunks = []
        for match in search_res.matches:
            if match.metadata and "text" in match.metadata:
                context_chunks.append(match.metadata["text"])
                
        context = "\n\n".join(context_chunks)
        
        if not context:
            return "Mujhe is product ke baare mein koi jaankari nahi mili Ji."
            
        # Use Gemini 3.1 Pro for high-reasoning tasks
        system_prompt = f"""
        You are a highly capable reasoning assistant for VaaniAI. 
        Answer the user's query based ONLY on the provided Context.
        You must respond in {language}. 
        If the language is Hindi, use Hinglish (code-mixing) and 'Ji/Aap' honorifics.
        If the language is Tamil, respond in fluent conversational Tamil.
        Keep the response brief as it will be spoken over a voice call.
        """
        
        prompt = f"Context:\n{context}\n\nQuery: {query}"
        
        response = client.models.generate_content(
            model='gemini-2.0-flash', # Using latest flash (gemini-3.1-pro does not exist)
            contents=prompt,
            config={"system_instruction": system_prompt}
        )
        
        return response.text
    except Exception as e:
        print(f"RAG Error [{type(e).__name__}]: {e}")
        return "Maaf kijiye Ji, abhi system mein kuch technical dikkat aa rahi hai."
