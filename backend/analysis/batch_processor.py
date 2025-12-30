import os
import psycopg2
from dotenv import load_dotenv
from sentiment_eng import ToneAnalyzer

load_dotenv()

def process_transcript_sentences():
    analyzer = ToneAnalyzer()
    try:
        connection = psycopg2.connect(os.getenv("DATABASE_URL"))
    except Exception as e:
        print(f"Database connection failed: {e}")
        return

    try:
        with connection:
            with connection.cursor() as cur:
                fetch_query = """
                    SELECT t.id, t.content
                    FROM transcripts t
                    LEFT JOIN transcript_sentences s ON t.id = s.transcript_id
                    WHERE s.id IS NULL
                    LIMIT 20;
                """
                cur.execute(fetch_query)
                paragraphs = cur.fetchall()

                if not paragraphs:
                    print("No transcripts left to process!")
                    return

                for p_id, content in paragraphs:
                    print(f"Processing transcript ID: {p_id}")
                    
                    analysis_result = analyzer.analyze_paragraph(content)
                    
                    if not analysis_result or not analysis_result.sentences:
                        continue

                    insert_sql = """
                        INSERT INTO transcript_sentences 
                        (transcript_id, sentence_text, topic, stance_score, impact_weight, reasoning)
                        VALUES (%s, %s, %s, %s, %s, %s);
                    """
                    
                    sentence_data = [
                        (p_id, s.text, s.topic, s.score, s.weight, s.reasoning)
                        for s in analysis_result.sentences
                    ]
                    
                    cur.executemany(insert_sql, sentence_data)
                    print(f"Successfully inserted {len(sentence_data)} sentences for ID {p_id}")

    except Exception as e:
        print(f"An error occurred during processing: {e}")
    finally:
        connection.close()

if __name__ == "__main__":
    process_transcript_sentences()