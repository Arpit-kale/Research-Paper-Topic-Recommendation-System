-- =====================================================================
-- Research Paper & Topic Recommendation System — Dashboard
-- SQLite schema + seed data (15 papers, 2018-2025, 6 themes)
-- This file is executed automatically by backend-flask/init_db.py
-- =====================================================================

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS report_meta;
CREATE TABLE report_meta (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  subtitle TEXT NOT NULL,
  author_name TEXT NOT NULL,
  author_class TEXT NOT NULL,
  roll_no TEXT NOT NULL,
  subject TEXT NOT NULL,
  review_period TEXT NOT NULL
);

INSERT INTO report_meta (id, title, subtitle, author_name, author_class, roll_no, subject, review_period) VALUES
(1, 'Research Paper & Topic Recommendation System',
    'A Literature Review of 15 Research Papers (2018-2025)',
    'Arpit Kale', 'CSE-AIML / A', 'A-31', 'Recommendation System', '2018-2025');

DROP TABLE IF EXISTS themes;
CREATE TABLE themes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  theme_no INTEGER NOT NULL,
  name TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  description TEXT NOT NULL,
  color TEXT NOT NULL DEFAULT '#4F6EF7',
  icon TEXT NOT NULL DEFAULT '📄'
);

INSERT INTO themes (id, theme_no, name, slug, description, color, icon) VALUES
(1, 1, 'Deep-Learning Foundations & Surveys', 'deep-learning-foundations-surveys',
 'General surveys establish how CNNs, RNNs, autoencoders, and LLM/GNN rankers model multimodal content and rich interconnection.',
 '#4F6EF7', '🧠'),
(2, 2, 'Scholarly Recommendation Surveys', 'scholarly-recommendation-surveys',
 'Domain-specific surveys map papers, citations, venues, and collaborators, cataloguing systems like CiteULike, Docear, and Mendeley.',
 '#10B981', '📚'),
(3, 3, 'Citation & Content-Based Methods', 'citation-content-based-methods',
 'Latent paper-citation relations personalize recommendations without full-text access or large user bases, easing cold-start and copyright constraints.',
 '#8B5CF6', '🔗'),
(4, 4, 'GNNs for Papers, Conferences & Collaborators', 'gnns-papers-conferences-collaborators',
 'Graph-attention and temporal graph networks recommend conferences and collaborators from citation/coauthorship graphs.',
 '#F59E0B', '🕸️'),
(5, 5, 'Topic & Trend Forecasting', 'topic-trend-forecasting',
 'LLM-enhanced LightGCN separates newly explored from historical topics; Impact4Cast forecasts high-impact, not-yet-studied topic combinations.',
 '#06B6D4', '📈'),
(6, 6, 'Filter Bubbles & Serendipity', 'filter-bubbles-serendipity',
 'Accuracy-optimized recommenders risk narrowing exposure to novel work; skip-gram-based diversification shows serendipity can be designed in without losing relevance.',
 '#EF4444', '🎯');

DROP TABLE IF EXISTS research_papers;
CREATE TABLE research_papers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  theme_id INTEGER NOT NULL REFERENCES themes(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  authors_venue TEXT NOT NULL,
  year INTEGER NOT NULL,
  contribution TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'partially_solved' CHECK (status IN ('solved','partially_solved','open')),
  citation_count INTEGER,
  citations_updated_at TEXT
);

INSERT INTO research_papers (theme_id, title, authors_venue, year, contribution, status) VALUES
(1,'Deep Learning for Recommender Systems: A Survey','Zhang et al.',2019,'Establishes how CNNs, RNNs and autoencoders model multimodal recommendation content.','solved'),
(1,'Neural Approaches to Recommendation: An Overview','arXiv',2019,'Surveys neural recommender architectures and their applicability to structured content.','solved'),
(1,'LLM and GNN-Based Ranking: A Modern Survey','Neural Computing & Applications',2025,'Reviews how LLM/GNN rankers model rich interconnection between items.','partially_solved'),
(2,'A Comprehensive Survey of Scholarly Recommender Systems','Beel et al.',2016,'Maps papers, citations, venues and collaborators; catalogues systems like CiteULike and Docear.','solved'),
(2,'Scholarly Recommendation Systems: State of the Art','IEEE Access',2020,'Surveys domain-specific recommenders and their evaluation practices.','partially_solved'),
(2,'Reference and Citation Recommendation Systems: A Survey','Knowledge & Information Systems',2023,'Catalogues Mendeley-like systems and citation recommendation pipelines.','partially_solved'),
(3,'A Citation-Based Recommender System for Scholarly Papers','Various',2018,'Uses latent paper-citation relations to personalize recommendations without full-text access, easing cold-start and copyright constraints.','solved'),
(4,'GraphConfRec: A Graph Neural Network Conference Recommender','Various',2021,'Graph-attention network recommends conferences from citation/coauthorship graphs.','solved'),
(4,'Temporal Graph Networks for Collaborator Recommendation','Zhu & Yaseen',2022,'Uses temporal graph networks to recommend research collaborators over time.','solved'),
(4,'GNN-KADR: Knowledge-Aware Deep Recommendation via GNNs','Various',2022,'Combines knowledge graphs with GNNs to boost recommendation quality under data sparsity.','partially_solved'),
(4,'GNN-RS: A Survey of Graph Neural Network Recommender Systems','Various',2023,'Surveys GNN-based recommender architectures across scholarly domains.','partially_solved'),
(5,'LLM-Enhanced LightGCN for Topic Discovery','Scientometrics',2025,'Separates newly explored topics from historical ones using LLM-enhanced graph convolution.','partially_solved'),
(5,'Impact4Cast: Forecasting High-Impact Topic Combinations','Gu & Krenn',2024,'Forecasts high-impact, not-yet-studied topic combinations before they emerge.','open'),
(6,'Beyond Accuracy: A Review of Filter Bubbles in Recommender Systems','Various',2023,'Shows accuracy-optimized recommenders risk narrowing a researcher''s exposure to novel work.','open'),
(6,'Skip-Gram Based Diversification for Serendipitous Recommendation','KDD',2019,'Demonstrates serendipity can be designed into recommenders without sacrificing relevance.','solved');

DROP TABLE IF EXISTS key_findings;
CREATE TABLE key_findings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  category TEXT NOT NULL CHECK (category IN ('works_well','open_challenge')),
  description TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0
);

INSERT INTO key_findings (category, description, sort_order) VALUES
('works_well','Citation-based latent models ease cold-start without full-text or large user bases',1),
('works_well','Graph-attention and temporal GNNs beat LightGCN/GBT baselines for conferences & collaborators',2),
('works_well','LLM-enhanced graphs improve both personalization and topic diversity',3),
('works_well','Knowledge graphs boost quality under data sparsity via multi-hop relations',4),
('works_well','Skip-gram diversification injects serendipity without sacrificing relevance',5),
('open_challenge','Accuracy-optimized recommenders still risk filter bubbles and narrowed exposure',1),
('open_challenge','Beyond-accuracy goals — diversity, fairness, explainability — remain underexplored',2),
('open_challenge','Copyright-restricted full text still limits purely content-based approaches',3),
('open_challenge','Forecasting genuinely novel, not-yet-studied topic combinations is still hard',4),
('open_challenge','Evaluation practice across studies remains inconsistent, hindering comparison',5);

DROP TABLE IF EXISTS research_gap;
CREATE TABLE research_gap (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  summary TEXT NOT NULL,
  gap_statement TEXT NOT NULL,
  closing_statement TEXT NOT NULL
);

INSERT INTO research_gap (id, summary, gap_statement, closing_statement) VALUES
(1,
'Across the fifteen reviewed papers, the field has moved from classical content- and citation-based recommenders toward graph neural network and LLM-enhanced architectures that fuse text, citation graphs, and coauthorship networks — while a growing body of evaluation research warns that accuracy-optimized recommendation can narrow a researcher''s exploration.',
'No existing system jointly optimizes recommendation accuracy, exploration-friendly diversity, forward-looking topic forecasting, and fairness/cold-start robustness within one deployable framework — most papers strengthen only one or two of these dimensions at a time.',
'This gap sets the direction for future work: a single, deployable recommender that is accurate, exploration-friendly, and forecasting-aware for real-world scholarly use.');

DROP TABLE IF EXISTS future_works;
CREATE TABLE future_works (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0
);

INSERT INTO future_works (title, description, sort_order) VALUES
('Fuse GNN Structure with LLM Semantics','Combine GNN-based structural signals with LLM-derived semantics for both accuracy and richer topic understanding.',1),
('Diversity- & Serendipity-Aware Ranking','Design explicit diversity- and serendipity-aware ranking that avoids reinforcing a researcher''s existing specialization.',2),
('Extend Cold-Start to Emerging Topics','Extend cold-start solutions (citation-based, content-profile) to newly emerging topics, not only new papers.',3),
('Standardized Beyond-Accuracy Evaluation','Build standardized, beyond-accuracy evaluation — diversity, fairness, explainability — to enable fair comparison across systems.',4);

DROP TABLE IF EXISTS reading_list;
CREATE TABLE reading_list (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  authors TEXT,
  venue TEXT,
  year INTEGER,
  doi TEXT,
  url TEXT,
  abstract TEXT,
  source TEXT,
  tags TEXT DEFAULT '',
  notes TEXT DEFAULT '',
  status TEXT NOT NULL DEFAULT 'unread' CHECK (status IN ('unread','read')),
  bookmarked_at TEXT
);

DROP TABLE IF EXISTS users;
CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL
);

-- password is "password" (werkzeug pbkdf2 hash, generated at init_db.py time in practice;
-- this row is a placeholder and gets replaced by init_db.py with a real hash)
INSERT INTO users (name, email, password_hash) VALUES
('Arpit Kale', 'admin@dashboard.test', 'placeholder');
