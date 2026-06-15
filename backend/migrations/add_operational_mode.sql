-- Add operational_mode enum type
CREATE TYPE operational_mode AS ENUM ('LEARN', 'CLARIFICATION', 'EXECUTION', 'TROUBLESHOOTING');

-- Add column to knowledge_chunks
ALTER TABLE knowledge_chunks 
ADD COLUMN operational_mode operational_mode DEFAULT 'LEARN';

-- Update match function to support mode filtering
CREATE OR REPLACE FUNCTION match_knowledge_chunks_with_mode(
  query_embedding vector(768),
  match_threshold float,
  match_count int,
  filter_mode operational_mode DEFAULT NULL
)
RETURNS TABLE (
  chunk_id uuid,
  config_id uuid,
  order_index int,
  title text,
  content text,
  parent_path text,
  current_path text,
  tags text[],
  synthetic_questions text[],
  similarity float
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    k.chunk_id,
    k.config_id,
    k.order_index,
    k.title,
    k.content,
    k.parent_path,
    k.metadata->>'current_path' as current_path,
    k.tags,
    k.synthetic_questions,
    1 - (k.embedding <=> query_embedding) AS similarity
  FROM knowledge_chunks k
  WHERE 1 - (k.embedding <=> query_embedding) > match_threshold
    AND (filter_mode IS NULL OR k.operational_mode = filter_mode)
  ORDER BY k.embedding <=> query_embedding
  LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- Update lexical match function to support mode filtering
CREATE OR REPLACE FUNCTION match_knowledge_chunks_lexical_with_mode(
  query_text text,
  match_threshold float,
  match_limit int,
  filter_mode operational_mode DEFAULT NULL
)
RETURNS TABLE (
  chunk_id uuid,
  config_id uuid,
  order_index int,
  title text,
  content text,
  parent_path text,
  current_path text,
  tags text[],
  synthetic_questions text[],
  similarity float
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    k.chunk_id,
    k.config_id,
    k.order_index,
    k.title,
    k.content,
    k.parent_path,
    k.metadata->>'current_path' as current_path,
    k.tags,
    k.synthetic_questions,
    strict_word_similarity(query_text, k.content) AS similarity
  FROM knowledge_chunks k
  WHERE strict_word_similarity(query_text, k.content) > match_threshold
    AND (filter_mode IS NULL OR k.operational_mode = filter_mode)
  ORDER BY similarity DESC
  LIMIT match_limit;
END;
$$ LANGUAGE plpgsql;
