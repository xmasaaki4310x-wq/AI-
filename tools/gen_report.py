#!/usr/bin/env python3
"""Generate the next AI Daily Business Intelligence report.

Daily workflow (run by the Claude session that maintains this site):
1. Collect fresh AI news via web search (RSS is blocked in the runtime env).
2. Update ITEMS below: add new stories (pill "NEW"), keep recent ones
   ("SEEN") with slightly decayed scores, drop stale ones. Keep 40+ items;
   the top 40 by score are included.
3. Add a natural Japanese headline to JA_TITLES for every new story.
   The script warns about missing translations instead of falling back to
   machine translation.
4. Run: python3 tools/gen_report.py
   Writes ai_daily_intel_<JST timestamp>.html, overwrites latest.html and
   inserts an archive entry into index.html (idempotent per filename).
5. Commit, push, open a PR to gh-pages, merge.

Timestamps are JST because the site's "Generated JST" label says so.
"""
import html
import os
import re
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
NOW = datetime.now(JST)
STAMP = NOW.strftime("%Y-%m-%d %H:%M")
FILE_STAMP = NOW.strftime("%Y-%m-%d_%H%M")
LABEL = NOW.strftime("%Y-%m-%d %H%M")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- hand-written Japanese headlines (natural translation) ----------------
JA_TITLES = {
    "Redeploying Claude Fable 5":
        "Claude Fable 5、輸出規制の解除を受けて再展開",
    "Meet WebBrain: An Open-Source, Local-First AI Browser Agent That Reads Pages and Automates Tasks in Chrome and Firefox":
        "WebBrain登場:ページを読み取り操作を自動化する、オープンソースかつローカル動作のAIブラウザエージェント(Chrome/Firefox対応)",
    "UK's AI Security Institute finds standard benchmarks systematically underestimate what AI agents can actually do":
        "英AIセキュリティ研究所:標準ベンチマークはAIエージェントの実力を体系的に過小評価していると判明",
    "Anthropic invests $100 million into the Claude Partner Network":
        "Anthropic、Claudeパートナーネットワークに1億ドルを投資",
    "Introducing Web Search on Amazon Bedrock AgentCore":
        "Amazon Bedrock AgentCoreにWeb検索機能を導入",
    "New Claude Mythos becomes the first AI model to clear all cyberattack simulations from Britain's AI safety agency":
        "新Claude Mythos、英AI安全機関のサイバー攻撃シミュレーションを全通過した初のAIモデルに",
    "Alibaba reportedly bans employees from using Claude Code":
        "Alibaba、従業員のClaude Code利用を禁止と報道",
    "Anthropic's Fable 5 is back worldwide after a two-week government ban over a jailbreak":
        "AnthropicのFable 5、ジェイルブレイクを巡る2週間の政府規制を経て世界で再提供",
    "Expanding our use of Google Cloud TPUs and Services":
        "Anthropic、Google Cloud TPUとサービスの利用を拡大",
    "Agent-guided workflows to accelerate model customization in Amazon SageMaker AI":
        "Amazon SageMaker AI、エージェント主導のワークフローでモデルのカスタマイズを高速化",
    "Anthropic Launches Claude Science Beta: A Multi-Agent AI Workbench for Reproducible Genomics, Proteomics, and Cheminformatics Pipelines":
        "Anthropic、Claude Science(ベータ)を公開:再現可能なゲノム・プロテオーム・ケモインフォマティクス解析向けのマルチエージェントAIワークベンチ",
    "Microsoft follows Anthropic and OpenAI into the AI super app race with overhauled Copilot and AutoPilot agents":
        "Microsoft、刷新版CopilotとAutoPilotエージェントでAnthropic・OpenAIに続き「AIスーパーアプリ」競争へ",
    "OpenAI and Broadcom unveil \"Jalapeño,\" a custom chip built for LLM inference":
        "OpenAIとBroadcom、LLM推論向けカスタムチップ「Jalapeño」を発表",
    "Anthropic Redeploys Claude Fable 5 on July 1 After US Export Controls Lift, Adds New Cybersecurity Classifier":
        "Anthropic、米輸出規制の解除を受けClaude Fable 5を7月1日に再展開—新たなサイバーセキュリティ分類器も追加",
    "New in Amazon Bedrock AgentCore: Build agents with broader knowledge and continuous learning":
        "Amazon Bedrock AgentCoreの新機能:より広い知識と継続学習を備えたエージェントを構築",
    "Get started with the Claude apps gateway for Google Cloud":
        "Google Cloud向けClaudeアプリゲートウェイを使い始める",
    "LlamaIndex 'legal-kb': Agentic Retrieval over Index v2 with retrieve, find, read, and grep Tools":
        "LlamaIndex「legal-kb」:retrieve・find・read・grepツールでIndex v2をエージェント的に検索",
    "New data from OpenAI and Anthropic show how people actually use ChatGPT and Claude":
        "OpenAIとAnthropicの新データ、ChatGPTとClaudeの実際の使われ方を明らかに",
    "Microsoft launches its own AI deployment company with $2.5 billion commitment":
        "Microsoft、25億ドルを投じて自社のAI導入会社を設立",
    "Cloudflare's new policy pushes AI companies to pay for publishers' content":
        "Cloudflareの新方針、AI企業に出版社コンテンツの対価支払いを迫る",
    "AI industry finds its 2026 narrative as OpenAI and Microsoft argue users are the bottleneck, not models":
        "OpenAIとMicrosoft、「ボトルネックはモデルではなくユーザー」と主張—AI業界が2026年の物語を見出す",
    "Anthropic opens Seoul office and announces new partnerships across the Korean AI ecosystem":
        "Anthropic、ソウルオフィスを開設し韓国AIエコシステムで新たな提携を発表",
    "Efficiently serve dozens of fine-tuned models with vLLM on Amazon SageMaker AI and Amazon Bedrock":
        "Amazon SageMaker AIとBedrock上のvLLMで、数十のファインチューニング済みモデルを効率的に提供",
    "Stanford's AI Index 2026 shows rapid progress, growing safety concerns, and declining public trust":
        "スタンフォードAI Index 2026、急速な進歩と高まる安全性の懸念、低下する社会的信頼を示す",
    "What is Mistral AI? Everything to know about the OpenAI competitor":
        "Mistral AIとは?OpenAIの競合について知っておくべきこと",
    "Mistral AI Releases Leanstral 1.5: An Apache-2.0 Lean 4 Code Agent Model Solving 587 of 672 PutnamBench Problems":
        "Mistral AI、Leanstral 1.5を公開:PutnamBench 672問中587問を解くApache-2.0のLean 4コードエージェントモデル",
    "AlloyDB AI Functions - now with revolutionary performance boosts and cost savings":
        "AlloyDB AI Functions:大幅な性能向上とコスト削減を実現",
    "Safely Releasing Frontier Models to Customers":
        "フロンティアモデルを顧客へ安全に提供する",
    "Simplify model selection in Amazon Bedrock with the open source Model Profiler":
        "オープンソースのModel ProfilerでAmazon Bedrockのモデル選定を簡素化",
    "OpenAI cofounder envisions \"almost no interface\" future where nobody learns software anymore":
        "OpenAI共同創業者、誰もソフトの使い方を学ばない「ほぼインターフェースのない」未来を描く",
    "Security vulnerability reports have exploded since AI models started hunting for bugs":
        "AIモデルがバグ探索を始めて以降、セキュリティ脆弱性の報告が急増",
    "Anthropic launches Claude Science, an AI workspace built specifically for researchers":
        "Anthropic、研究者専用のAIワークスペース「Claude Science」を公開",
    "Meta quietly launches vibe-coded gaming app Pocket":
        "Meta、“バイブコーディング”で作ったゲームアプリ「Pocket」を静かに公開",
    "How Amazon Bedrock catches AI-generated phishing":
        "Amazon Bedrockはどうやって生成AI製フィッシングを検知するか",
    "Venice AI becomes a unicorn with $65M Series A as its privacy-first AI platform takes off":
        "プライバシー重視のVenice AI、6,500万ドルのシリーズAでユニコーンに",
    "Mark Zuckerberg tells staff that AI agents haven't progressed as quickly as he'd hoped":
        "ザッカーバーグ、社員に「AIエージェントは期待ほど速く進歩していない」と語る",
    "Anthropic is discussing a new custom chip with Samsung":
        "Anthropic、Samsungと新たなカスタムチップを協議",
    "Anthropic wants to develop its own drugs":
        "Anthropic、自社での創薬を目指す",
    "RAG-Anything Tutorial: Build a Multimodal Retrieval Pipeline for Text, Tables, Equations, and Images in Colab":
        "RAG-Anythingチュートリアル:テキスト・表・数式・画像に対応したマルチモーダル検索パイプラインをColabで構築",
    "Anthropic launches its own drug discovery programs to tackle diseases Big Pharma considers unprofitable":
        "Anthropic、大手製薬が不採算とみなす疾患に挑む自社創薬プログラムを開始",
    "Introducing Claude Sonnet 5":
        "Claude Sonnet 5を発表",
    "Gemini Spark, Google's agentic assistant, is now available on Mac":
        "Googleのエージェント型アシスタント「Gemini Spark」、Macで利用可能に",
    "Claude Science, an AI workbench for scientists, is now available":
        "科学者向けAIワークベンチ「Claude Science」が利用可能に",
    "Run NVIDIA Nemotron and OpenAI GPT OSS models on Amazon Bedrock in AWS GovCloud (US)":
        "AWS GovCloud(US)のAmazon BedrockでNVIDIA NemotronとOpenAI GPT OSSモデルを実行",
    "Structured memory filtering with metadata in AgentCore Memory":
        "AgentCore Memoryにおけるメタデータを使った構造化メモリのフィルタリング",
    "Multi-Agent Teams Hold Experts Back":
        "マルチエージェント・チームは専門家の足を引っ張る",
    "Best practices for multi-turn reinforcement learning in Amazon SageMaker AI":
        "Amazon SageMaker AIでのマルチターン強化学習のベストプラクティス",
    "Meet Alibaba's Page Agent: A JavaScript In-Page GUI Agent That Controls Web Interfaces With Natural Language Through the DOM":
        "Alibabaの「Page Agent」登場:DOM経由・自然言語でWeb画面を操作するJavaScript製のページ内GUIエージェント",
    "The latest AI news we announced in June 2026":
        "2026年6月に発表した最新AIニュースまとめ",
    "Building a serverless A2A gateway for agent discovery, routing, and access control":
        "エージェントの発見・ルーティング・アクセス制御のためのサーバーレスA2Aゲートウェイを構築",
    "AI explained: Why the world needs to act now":
        "解説:世界がいまAIに対処すべき理由—国連グローバルAIガバナンス対話がジュネーブで開幕",
    "Amazon Bedrock AgentCore harness is now generally available: Go from idea to production-grade agent in minutes":
        "Amazon Bedrock AgentCore harnessが一般提供に:アイデアから本番品質エージェントまで数分で",
    "Tencent releases Hy3 open-source model that allegedly matches models up to five times its active size":
        "Tencent、オープンソースモデル「Hy3」を公開—アクティブサイズの最大5倍のモデルに匹敵と主張",
    "Zhipu AI launches ZCode to challenge Claude Code and OpenAI Codex at a fraction of the cost":
        "智譜AI、「ZCode」を公開—Claude CodeとOpenAI Codexに数分の一のコストで挑戦",
    "OpenAI models and Codex on Amazon Bedrock are now generally available":
        "OpenAIモデルとCodex、Amazon Bedrockで一般提供開始",
    "OpenAI's genomics paper accidentally reveals a Pro lineup it hasn't announced yet":
        "OpenAIのゲノミクス論文、未発表の「GPT-5.6 Pro」3モデル構成を図らずも公開",
    "Trump drops restrictions on Anthropic's Mythos and Fable models":
        "トランプ政権、AnthropicのMythos・Fableモデルへの規制を撤廃",
    "Meituan Releases LongCat-2.0: A 1.6T-Parameter Open MoE Model with Native 1M Context and LongCat Sparse Attention":
        "Meituan、LongCat-2.0を公開:ネイティブ100万トークン文脈対応・1.6兆パラメータのオープンMoEモデル",
    "Tesla caps employee AI spending at $200 per week":
        "Tesla、従業員のAI利用支出を週200ドルに制限",
    "Deepseek topped Ramp's trending software vendors in June 2026 as US companies chase cheaper AI":
        "DeepSeek、Rampの6月急上昇ベンダー首位に—米企業がより安価なAIを志向",
    "Build context-rich research agents with Deep Agents and Bedrock AgentCore":
        "Deep AgentsとBedrock AgentCoreで文脈豊かなリサーチエージェントを構築",
    "Democratizing business intelligence: BGL's journey with Claude Agent SDK and Amazon Bedrock AgentCore":
        "BIの民主化:Claude Agent SDKとAmazon Bedrock AgentCoreによるBGLの取り組み",
    "Nvidia's Kyber NVL144 reportedly pushed back more than a year, Asian suppliers drop":
        "NVIDIAの次期AIサーバー「Kyber NVL144」に1年超の延期報道—アジアのサプライヤー株が下落",
    "ByteDance's Seedance 2.5 breaks the 30-second barrier for AI video generation":
        "ByteDanceのSeedance 2.5、AI動画生成の「30秒の壁」を突破",
    "AI private schools sell wealthy US families on personalized learning over traditional education":
        "AIプライベートスクール、米富裕層家庭に従来教育に代わる「個別最適化学習」を売り込む",
}

MISSING_JA = []

def localise(title: str) -> str:
    if title not in JA_TITLES:
        MISSING_JA.append(title)
        return title
    return JA_TITLES[title]

ANGLES = {
    "agent": "AIエージェント活用のニュースです。単発のチャット利用から、複数手順の業務実行へ移るタイミングを測る材料になります。",
    "risk": "AIエージェントを人のように管理する必要が高まっています。権限、監査ログ、事故対応を含めた社内AI運用ルールの検討材料です。",
    "platform": "開発・運用基盤の変化です。既存プロダクトへの組み込みや、運用コスト削減につながるか確認します。",
    "model": "モデル性能や提供形態の変化です。すぐ導入するより、既存ツールとの差分や次の検証テーマとして追跡します。",
    "partner": "AI導入を単体ツールではなく、販売代理店・クラウド契約・既存SI経由で広げる動きです。自社の販売チャネルや顧客導入支援に転用できるか見ます。",
    "market": "市場・競合の動きとして確認。自社の提案、商品企画、顧客コミュニケーションに使えるかを見ます。",
    "privacy": "データ所在地とモデル利用を両立する話です。欧州・大企業・規制産業の顧客にAIを提案する場合、導入条件の整理に使えます。",
}

# item: (title, url, source, weight_label, date, pill, score, themes, angle_key, signals, summary)
ITEMS = [
    ("Redeploying Claude Fable 5",
     "https://www.anthropic.com/news/redeploying-fable-5",
     "Anthropic News", 20, "date unknown", "SEEN", 52,
     "モデル/API、規制・リスク", "risk",
     ["source weight +20", "launch", "model", "security", "product/news signal"],
     "As of June 30, 2026, the US export controls on Fable 5 and Mythos 5 have been lifted. Fable 5 returned to users worldwide on July 1 across the Claude Platform, Claude.ai, Claude Code, and Claude Cowork, together with a new cybersecurity classifier and an industry framework for assessing jailbreak severity developed with Amazon, Microsoft, and Google."),
    ("Meet WebBrain: An Open-Source, Local-First AI Browser Agent That Reads Pages and Automates Tasks in Chrome and Firefox",
     "https://www.marktechpost.com/2026/07/02/meet-webbrain-an-open-source-local-first-ai-browser-agent-that-reads-pages-and-automates-tasks-in-chrome-and-firefox/",
     "MarkTechPost", 8, "2026-07-03", "SEEN", 46,
     "AIエージェント、モデル/API、クラウド、規制・リスク", "privacy",
     ["source weight +8", "privacy", "api", "agent", "model"],
     "WebBrain is a free, MIT-licensed AI browser agent for Chrome and Firefox. It reads pages, extracts data, and automates multi-step tasks through Ask and Act modes. Run it on local models like llama.cpp or Ollama for privacy, or connect any cloud API."),
    ("UK's AI Security Institute finds standard benchmarks systematically underestimate what AI agents can actually do",
     "https://the-decoder.com/uks-ai-security-institute-finds-standard-benchmarks-systematically-underestimate-what-ai-agents-can-actually-do/",
     "The Decoder", 12, "2026-07-04", "SEEN", 45,
     "AIエージェント、モデル/API、規制・リスク、研究", "risk",
     ["source weight +12", "security", "agent", "agents", "model"],
     "In a study covering seven benchmarks, the UK's AI Security Institute shows that standard AI evaluations systematically underestimate agent capabilities by capping the compute budget. On software engineering tasks, success rates jumped about 25 percent when the cap was lifted."),
    ("Anthropic invests $100 million into the Claude Partner Network",
     "https://www.anthropic.com/news/claude-partner-network",
     "Anthropic News", 20, "date unknown", "SEEN", 45,
     "法人導入、買収・提携", "partner",
     ["source weight +20", "partnership", "partners", "enterprise", "product/news signal"],
     "Anthropic is investing $100 million into the Claude Partner Network to accelerate enterprise deployments through consultancies, system integrators, and cloud marketplaces."),
    ("Introducing Web Search on Amazon Bedrock AgentCore",
     "https://aws.amazon.com/blogs/machine-learning/introducing-web-search-on-amazon-bedrock-agentcore/",
     "AWS Machine Learning Blog", 12, "2026-07-03", "SEEN", 44,
     "法人導入、AIエージェント、クラウド", "agent",
     ["source weight +12", "agent", "agents", "search", "enterprise"],
     "AWS announced general availability of Web Search on Amazon Bedrock AgentCore, a fully managed MCP tool that grounds agent responses in current, cited web knowledge with zero data egress from the customer's AWS environment, built on Amazon's own search infrastructure."),
    ("New Claude Mythos becomes the first AI model to clear all cyberattack simulations from Britain's AI safety agency",
     "https://the-decoder.com/new-claude-mythos-becomes-the-first-ai-model-to-clear-all-cyberattack-simulations-from-britains-ai-safety-agency/",
     "The Decoder", 12, "2026-07-05", "SEEN", 43,
     "モデル/API、規制・リスク、研究", "risk",
     ["source weight +12", "security", "model", "benchmark", "fresh"],
     "Claude Mythos is the first AI model to clear every cyberattack simulation run by Britain's AI safety agency, a milestone for capability evaluations that also sharpens the debate over how dual-use skills should be gated and monitored."),
    ("Alibaba reportedly bans employees from using Claude Code",
     "https://techcrunch.com/2026/07/04/alibaba-reportedly-bans-employees-from-using-claude-code/",
     "TechCrunch AI", 16, "2026-07-04", "SEEN", 42,
     "法人導入、市場動向、規制・リスク", "market",
     ["source weight +16", "enterprise", "risk", "fresh", "product/news signal"],
     "China's Alibaba will ban employees from using Anthropic's programming tool Claude Code starting July 10. Anthropic already prohibits Chinese companies and their foreign subsidiaries from using its models and has been closing loopholes that allowed access."),
    ("Anthropic's Fable 5 is back worldwide after a two-week government ban over a jailbreak",
     "https://the-decoder.com/anthropics-fable-5-is-back-worldwide-after-a-two-week-government-ban-over-a-jailbreak/",
     "The Decoder", 12, "2026-07-04", "SEEN", 41,
     "モデル/API、規制・リスク", "risk",
     ["source weight +12", "security", "model", "risk", "fresh"],
     "Fable 5 is available worldwide again after the US Department of Commerce lifted the export controls imposed on June 12 over a jailbreak incident. Anthropic redeployed the model on July 1 with an additional cybersecurity classifier in place."),
    ("Expanding our use of Google Cloud TPUs and Services",
     "https://www.anthropic.com/news/expanding-our-use-of-google-cloud-tpus-and-services",
     "Anthropic News", 20, "date unknown", "SEEN", 41,
     "クラウド、買収・提携", "partner",
     ["source weight +20", "cloud", "partnership", "product/news signal"],
     "Anthropic is expanding its use of Google Cloud TPUs and services to scale training and inference capacity, deepening the compute partnership behind the Claude model family."),
    ("Agent-guided workflows to accelerate model customization in Amazon SageMaker AI",
     "https://aws.amazon.com/blogs/machine-learning/agent-guided-workflows-to-accelerate-model-customization-in-amazon-sagemaker-ai/",
     "AWS Machine Learning Blog", 12, "2026-07-03", "SEEN", 40,
     "AIエージェント、モデル/API、クラウド", "platform",
     ["source weight +12", "agent", "workflow", "model", "cloud"],
     "Amazon SageMaker AI now offers an agentic experience where developers describe their use case in natural language and an AI coding agent streamlines the journey from data preparation through technique selection, evaluation, and deployment."),
    ("Anthropic Launches Claude Science Beta: A Multi-Agent AI Workbench for Reproducible Genomics, Proteomics, and Cheminformatics Pipelines",
     "https://www.marktechpost.com/2026/07/04/anthropic-launches-claude-science-beta/",
     "MarkTechPost", 8, "2026-07-05", "SEEN", 40,
     "AIエージェント、モデル/API", "agent",
     ["source weight +8", "launch", "agent", "model", "models"],
     "Anthropic released Claude Science in beta on June 30, 2026. The app runs on existing Claude models. A coordinating agent delegates to domain specialists, a reviewer agent flags and corrects citations and numbers, and every figure ships with its exact code and environment."),
    ("Microsoft follows Anthropic and OpenAI into the AI super app race with overhauled Copilot and AutoPilot agents",
     "https://the-decoder.com/microsoft-follows-anthropic-and-openai-into-the-ai-super-app-race-with-overhauled-copilot-and-autopilot-agents/",
     "The Decoder", 12, "2026-07-04", "SEEN", 39,
     "法人導入、AIエージェント", "agent",
     ["source weight +12", "enterprise", "agent", "agents", "copilot"],
     "Microsoft reportedly plans to merge its consumer and enterprise Copilot apps into a single app in August. Rarely used features like Copilot Podcasts are getting cut, and new AI agents called \"AutoPilot\" will handle tasks in the background for an extra fee."),
    ("OpenAI and Broadcom unveil \"Jalapeño,\" a custom chip built for LLM inference",
     "https://the-decoder.com/openai-and-broadcom-unveil-jalapeno-a-custom-chip-built-for-llm-inference/",
     "The Decoder", 12, "2026-07-05", "SEEN", 39,
     "買収・提携、市場動向", "partner",
     ["source weight +12", "partnership", "inference", "model", "fresh"],
     "OpenAI and Broadcom unveiled Jalapeño, a custom accelerator designed specifically for large language model inference, the first tangible product of their multi-year chip co-development deal."),
    ("Anthropic Redeploys Claude Fable 5 on July 1 After US Export Controls Lift, Adds New Cybersecurity Classifier",
     "https://www.marktechpost.com/2026/07/01/anthropic-redeploys-claude-fable-5-on-july-1-after-us-export-controls-lift-adds-new-cybersecurity-classifier/",
     "MarkTechPost", 8, "2026-07-01", "SEEN", 39,
     "モデル/API、規制・リスク", "risk",
     ["source weight +8", "security", "launch", "model", "deployment"],
     "Anthropic redeployed Claude Fable 5 on July 1 after the US Department of Commerce lifted export controls. The rollout adds a new cybersecurity classifier and ships alongside a cross-industry framework for scoring jailbreak severity."),
    ("New in Amazon Bedrock AgentCore: Build agents with broader knowledge and continuous learning",
     "https://aws.amazon.com/blogs/machine-learning/new-in-amazon-bedrock-agentcore-build-agents-with-broader-knowledge-and-continuous-learning/",
     "AWS Machine Learning Blog", 12, "2026-07-02", "SEEN", 38,
     "法人導入、AIエージェント、クラウド", "agent",
     ["source weight +12", "agent", "agents", "enterprise", "data"],
     "Amazon Bedrock AgentCore adds broader knowledge grounding and continuous learning so deployed agents can keep improving from operational feedback while meeting enterprise governance requirements."),
    ("Get started with the Claude apps gateway for Google Cloud",
     "https://cloud.google.com/blog/topics/developers-practitioners/announcing-claude-apps-gateway-for-google-cloud/",
     "Google Cloud AI & ML", 12, "2026-07-02", "SEEN", 38,
     "法人導入、AIエージェント、モデル/API、クラウド", "agent",
     ["source weight +12", "enterprise", "platform", "agent", "cloud"],
     "Anthropic's agentic coding tool Claude Code has worked with Google Cloud for a while now. An individual developer could easily point CLAUDE_CODE_USE_VERTEX=1 at a Google Cloud (GCP) project, grant the role roles/aiplatform.user, and inference stays inside your project."),
    ("LlamaIndex 'legal-kb': Agentic Retrieval over Index v2 with retrieve, find, read, and grep Tools",
     "https://www.marktechpost.com/2026/07/05/llamaindex-legal-kb-agentic-retrieval-over-index-v2-with-retrieve-find-read-and-grep-tools/",
     "MarkTechPost", 8, "2026-07-05", "SEEN", 37,
     "AIエージェント、モデル/API", "agent",
     ["source weight +8", "agent", "api", "workflow", "fresh"],
     "LlamaIndex released legal-kb, a reference app exposing Index v2 retrieval as agent tools: retrieve, find, read, and grep. It shows how agentic retrieval patterns replace one-shot RAG pipelines for legal knowledge bases."),
    ("New data from OpenAI and Anthropic show how people actually use ChatGPT and Claude",
     "https://the-decoder.com/new-data-from-openai-and-anthropic-show-how-people-actually-use-chatgpt-and-claude/",
     "The Decoder", 12, "2026-07-05", "SEEN", 37,
     "市場動向、研究", "market",
     ["source weight +12", "data", "market", "model", "fresh"],
     "New usage studies from OpenAI and Anthropic detail how people actually use ChatGPT and Claude, giving planners real-world category splits between work tasks, coding, writing, and personal use."),
    ("Microsoft launches its own AI deployment company with $2.5 billion commitment",
     "https://techcrunch.com/2026/07/02/microsoft-launches-its-own-ai-deployment-company-with-2-5-billion-commitment/",
     "TechCrunch AI", 16, "2026-07-02", "SEEN", 36,
     "法人導入", "platform",
     ["source weight +16", "launch", "deployment", "product/news signal"],
     "Microsoft follows Amazon, OpenAI, and Anthropic with its new AI deployment group."),
    ("Cloudflare's new policy pushes AI companies to pay for publishers' content",
     "https://techcrunch.com/2026/07/01/cloudflares-new-policy-pushes-ai-companies-to-pay-for-publishers-content/",
     "TechCrunch AI", 16, "2026-07-02", "SEEN", 36,
     "AIエージェント、クラウド、規制・リスク", "agent",
     ["source weight +16", "agent", "agents", "cloud", "search"],
     "Cloudflare is giving AI companies until September 15 to separate web crawlers used for search from those used for AI training and agents, or risk being blocked by default on many publisher sites."),
    ("AI industry finds its 2026 narrative as OpenAI and Microsoft argue users are the bottleneck, not models",
     "https://the-decoder.com/ai-industry-finds-its-2026-narrative-as-openai-and-microsoft-argue-users-are-the-bottleneck-not-models/",
     "The Decoder", 12, "2026-07-05", "SEEN", 36,
     "市場動向", "market",
     ["source weight +12", "market", "model", "models", "fresh"],
     "OpenAI and Microsoft executives are converging on a new 2026 narrative: model capability is no longer the constraint on value — user adoption, workflow redesign, and organizational change are."),
    ("Anthropic opens Seoul office and announces new partnerships across the Korean AI ecosystem",
     "https://www.anthropic.com/news/seoul-office-partnerships-korean-ai-ecosystem",
     "Anthropic News", 20, "date unknown", "SEEN", 35,
     "買収・提携", "partner",
     ["source weight +20", "partnership", "partners", "product/news signal"],
     "Anthropic opens Seoul office and announces new partnerships across the Korean AI ecosystem"),
    ("Efficiently serve dozens of fine-tuned models with vLLM on Amazon SageMaker AI and Amazon Bedrock",
     "https://aws.amazon.com/blogs/machine-learning/efficiently-serve-dozens-of-fine-tuned-models-with-vllm-on-amazon-sagemaker-ai-and-amazon-bedrock/",
     "AWS Machine Learning Blog", 12, "2026-07-02", "SEEN", 35,
     "モデル/API、クラウド", "platform",
     ["source weight +12", "model", "models", "inference", "cloud"],
     "This post shows how to serve dozens of fine-tuned model variants efficiently with vLLM multi-LoRA serving on Amazon SageMaker AI and Amazon Bedrock, cutting idle GPU cost while keeping per-tenant isolation."),
    ("Stanford's AI Index 2026 shows rapid progress, growing safety concerns, and declining public trust",
     "https://the-decoder.com/stanfords-ai-index-2026-shows-rapid-progress-growing-safety-concerns-and-declining-public-trust/",
     "The Decoder", 12, "2026-07-04", "SEEN", 35,
     "研究、規制・リスク、市場動向", "market",
     ["source weight +12", "research", "safety", "data", "fresh"],
     "Stanford's AI Index 2026 documents rapid capability progress alongside growing safety concerns and declining public trust, a mix that shapes how enterprise buyers and regulators approach AI adoption this year."),
    ("What is Mistral AI? Everything to know about the OpenAI competitor",
     "https://techcrunch.com/2026/07/04/what-is-mistral-ai-everything-to-know-about-the-openai-competitor/",
     "TechCrunch AI", 16, "2026-07-05", "SEEN", 34,
     "モデル/API、資金調達", "model",
     ["source weight +16", "funding", "model", "models", "open source"],
     "Mistral AI, which offers some open source AI models, has raised significant funding since its creation in 2023, with the ambition to \"put frontier AI in the hands of everyone.\" A new open-weight model is planned for this summer with early access in July."),
    ("Mistral AI Releases Leanstral 1.5: An Apache-2.0 Lean 4 Code Agent Model Solving 587 of 672 PutnamBench Problems",
     "https://www.marktechpost.com/2026/07/03/mistral-ai-releases-leanstral-1-5-an-apache-2-0-lean-4-code-agent-model-solving-587-of-672-putnambench-problems/",
     "MarkTechPost", 8, "2026-07-04", "SEEN", 34,
     "法人導入、AIエージェント、モデル/API、研究", "agent",
     ["source weight +8", "agent", "model", "benchmark", "deployment"],
     "Mistral AI released Leanstral 1.5, a free Apache-2.0 code agent model for Lean 4. It saturates miniF2F and solves 587 of 672 PutnamBench problems. The 119B mixture-of-experts activates 6.5B parameters per token."),
    ("AlloyDB AI Functions - now with revolutionary performance boosts and cost savings",
     "https://cloud.google.com/blog/products/databases/boost-performance-and-lower-costs-with-alloydb-ai-functions/",
     "Google Cloud AI & ML", 12, "2026-07-02", "SEEN", 34,
     "AIエージェント、モデル/API", "platform",
     ["source weight +12", "agent", "agents", "model", "search"],
     "AlloyDB is an AI-native database—it isn't just a passive data store, it intelligently understands and processes your data. With AlloyDB, you get industry-leading vector and hybrid search, and near 100% accurate natural language-to-SQL capabilities."),
    ("Safely Releasing Frontier Models to Customers",
     "https://aws.amazon.com/blogs/machine-learning/safely-releasing-frontier-models-to-customers/",
     "AWS Machine Learning Blog", 12, "2026-07-01", "SEEN", 34,
     "法人導入、モデル/API、クラウド、規制・リスク", "risk",
     ["source weight +12", "customer", "customers", "security", "model"],
     "It's our goal for AWS to be the most secure place to run any workload, and in support of that we've been deeply investing in security across our services since AWS's inception more than two decades ago. Our AI services like Amazon Bedrock are built on this foundation."),
    ("Simplify model selection in Amazon Bedrock with the open source Model Profiler",
     "https://aws.amazon.com/blogs/machine-learning/simplify-model-selection-in-amazon-bedrock-with-the-open-source-model-profiler/",
     "AWS Machine Learning Blog", 12, "2026-07-02", "SEEN", 33,
     "モデル/API、クラウド", "platform",
     ["source weight +12", "api", "model", "open source", "search"],
     "The Amazon Bedrock Model Profiler is an open source tool that aggregates model metadata from multiple AWS APIs and external sources into a single, searchable interface."),
    ("OpenAI cofounder envisions \"almost no interface\" future where nobody learns software anymore",
     "https://the-decoder.com/openai-cofounder-envisions-almost-no-interface-future-where-nobody-learns-software-anymore/",
     "The Decoder", 12, "2026-07-04", "SEEN", 33,
     "AIエージェント、モデル/API", "agent",
     ["source weight +12", "agent", "market", "model", "models"],
     "Greg Brockman admits ChatGPT's plugins, heavily marketed in 2023, failed \"because the models weren't ready.\" Instead of app extensions, he sees the future in an invisible, context-aware agent."),
    ("Security vulnerability reports have exploded since AI models started hunting for bugs",
     "https://the-decoder.com/security-vulnerability-reports-have-exploded-since-ai-models-started-hunting-for-bugs/",
     "The Decoder", 12, "2026-07-04", "SEEN", 33,
     "モデル/API、規制・リスク", "risk",
     ["source weight +12", "security", "launch", "model", "models"],
     "Epoch AI reports a sharp rise in security vulnerability reports. In June 2026, 21 organizations reported about 1,500 high-severity and critical CVEs, more than 3.5 times the previous monthly record."),
    ("Anthropic launches Claude Science, an AI workspace built specifically for researchers",
     "https://the-decoder.com/anthropic-launches-claude-science-an-ai-workspace-built-specifically-for-researchers/",
     "The Decoder", 12, "2026-07-03", "SEEN", 32,
     "モデル/API、研究", "model",
     ["source weight +12", "launch", "research", "product/news signal"],
     "Anthropic launched Claude Science, an AI workspace built specifically for researchers that integrates the tools and packages scientists most often use and produces auditable artifacts."),
    ("Meta quietly launches vibe-coded gaming app Pocket",
     "https://techcrunch.com/2026/07/02/meta-quietly-launches-vibe-coded-gaming-app-pocket/",
     "TechCrunch AI", 16, "2026-07-03", "SEEN", 32,
     "市場動向", "market",
     ["source weight +16", "launch", "product/news signal"],
     "Meta has quietly launched Pocket, an experimental AI app that lets users generate and share interactive mini games using text prompts."),
    ("How Amazon Bedrock catches AI-generated phishing",
     "https://aws.amazon.com/blogs/machine-learning/how-amazon-bedrock-catches-ai-generated-phishing/",
     "AWS Machine Learning Blog", 12, "2026-07-03", "SEEN", 32,
     "クラウド、規制・リスク", "risk",
     ["source weight +12", "security", "launch", "open source", "risk"],
     "How Amazon Bedrock catches AI-generated phishing at scale, combining classifier ensembles with agentic triage."),
    ("Venice AI becomes a unicorn with $65M Series A as its privacy-first AI platform takes off",
     "https://techcrunch.com/2026/07/01/venice-ai-becomes-a-unicorn-with-65m-series-a-as-its-privacy-first-ai-platform-takes-off/",
     "TechCrunch AI", 16, "2026-07-01", "SEEN", 31,
     "資金調達、市場動向", "privacy",
     ["source weight +16", "revenue", "privacy", "platform"],
     "Venice AI becomes a unicorn with $65M Series A as its privacy-first AI platform takes off."),
    ("Mark Zuckerberg tells staff that AI agents haven't progressed as quickly as he'd hoped",
     "https://techcrunch.com/2026/07/02/mark-zuckerberg-tells-staff-that-ai-agents-havent-progressed-as-quickly-as-hed-hoped/",
     "TechCrunch AI", 16, "2026-07-03", "SEEN", 31,
     "AIエージェント、市場動向", "agent",
     ["source weight +16", "agent", "agents"],
     "Mark Zuckerberg tells staff that AI agents haven't progressed as quickly as he'd hoped."),
    ("Anthropic is discussing a new custom chip with Samsung",
     "https://techcrunch.com/2026/07/02/anthropic-is-discussing-a-new-custom-chip-with-samsung/",
     "TechCrunch AI", 16, "2026-07-03", "SEEN", 31,
     "買収・提携", "partner",
     ["source weight +16", "partnership", "partners"],
     "Anthropic is discussing a new custom chip with Samsung."),
    ("Anthropic wants to develop its own drugs",
     "https://www.theverge.com/ai-artificial-intelligence/961311/anthropic-claude-science-ai-drug-development",
     "The Verge AI", 12, "2026-07-03", "SEEN", 30,
     "研究、市場動向", "market",
     ["source weight +12", "launch", "model", "models", "data"],
     "Anthropic wants to develop its own drugs, building on Claude Science and its new drug discovery programs."),
    ("RAG-Anything Tutorial: Build a Multimodal Retrieval Pipeline for Text, Tables, Equations, and Images in Colab",
     "https://www.marktechpost.com/2026/07/02/rag-anything-tutorial-build-a-multimodal-retrieval-pipeline-for-text-tables-equations-and-images-in-colab/",
     "MarkTechPost", 8, "2026-07-03", "SEEN", 30,
     "モデル/API", "platform",
     ["source weight +8", "api", "workflow", "multimodal"],
     "RAG-Anything Tutorial: Build a Multimodal Retrieval Pipeline for Text, Tables, Equations, and Images in Colab."),
    ("Anthropic launches its own drug discovery programs to tackle diseases Big Pharma considers unprofitable",
     "https://the-decoder.com/anthropic-launches-its-own-drug-discovery-programs-to-tackle-diseases-big-pharma-considers-unprofitable/",
     "The Decoder", 12, "2026-07-04", "SEEN", 29,
     "研究、市場動向", "market",
     ["source weight +12", "launch", "product/news signal"],
     "Anthropic is launching its own drug development program for neglected diseases the pharmaceutical industry considers unprofitable. Novartis CEO Vas Narasimhan thinks AI could cut development time from twelve years to seven or eight."),
    ("Introducing Claude Sonnet 5",
     "https://www.anthropic.com/news/claude-sonnet-5",
     "Anthropic News", 20, "date unknown", "SEEN", 29,
     "モデル/API", "model",
     ["source weight +20", "agent", "agents"],
     "Sonnet 5 delivers frontier performance across coding, agents, and professional work at scale. It is now the default model for Free and Pro plans, with introductory pricing of $2 per million input tokens and $10 per million output tokens through August 31, 2026."),
    ("Gemini Spark, Google's agentic assistant, is now available on Mac",
     "https://techcrunch.com/2026/07/01/gemini-spark-googles-agentic-assistant-is-now-available-on-mac/",
     "TechCrunch AI", 16, "2026-07-01", "SEEN", 28,
     "AIエージェント", "agent",
     ["source weight +16", "agent", "product/news signal"],
     "Gemini Spark, Google's agentic assistant, is now available on Mac."),
    ("Claude Science, an AI workbench for scientists, is now available",
     "https://www.anthropic.com/news/claude-science-ai-workbench",
     "Anthropic News", 20, "date unknown", "SEEN", 28,
     "研究", "model",
     ["source weight +20", "search", "product/news signal"],
     "Claude Science is a customizable app that integrates the tools and packages researchers most often use, produces auditable artifacts, and provides flexible access to computing resources."),
    ("Run NVIDIA Nemotron and OpenAI GPT OSS models on Amazon Bedrock in AWS GovCloud (US)",
     "https://aws.amazon.com/blogs/machine-learning/run-nvidia-nemotron-and-openai-gpt-oss-models-on-amazon-bedrock-in-aws-govcloud-us/",
     "AWS Machine Learning Blog", 12, "2026-07-02", "SEEN", 27,
     "モデル/API、クラウド", "platform",
     ["source weight +12", "model", "models", "cloud", "inference"],
     "Run NVIDIA Nemotron and OpenAI GPT OSS models on Amazon Bedrock in AWS GovCloud (US)."),
    ("Structured memory filtering with metadata in AgentCore Memory",
     "https://aws.amazon.com/blogs/machine-learning/structured-memory-filtering-with-metadata-in-agentcore-memory/",
     "AWS Machine Learning Blog", 12, "2026-07-02", "SEEN", 27,
     "法人導入、AIエージェント", "agent",
     ["source weight +12", "enterprise", "agent", "data"],
     "Structured memory filtering with metadata in AgentCore Memory."),
    ("Multi-Agent Teams Hold Experts Back",
     "https://machinelearning.apple.com/research/multi-agent-teams-experts",
     "Apple Machine Learning Research", 8, "2026-07-02", "SEEN", 26,
     "AIエージェント、研究", "agent",
     ["source weight +8", "agent", "agents", "workflow"],
     "Multi-Agent Teams Hold Experts Back."),
    ("Best practices for multi-turn reinforcement learning in Amazon SageMaker AI",
     "https://aws.amazon.com/blogs/machine-learning/best-practices-for-multi-turn-reinforcement-learning-in-amazon-sagemaker-ai/",
     "AWS Machine Learning Blog", 12, "2026-07-03", "SEEN", 25,
     "モデル/API、研究", "platform",
     ["source weight +12", "agent", "evaluation"],
     "Best practices for multi-turn reinforcement learning in Amazon SageMaker AI."),
    ("Meet Alibaba's Page Agent: A JavaScript In-Page GUI Agent That Controls Web Interfaces With Natural Language Through the DOM",
     "https://www.marktechpost.com/2026/07/02/meet-alibabas-page-agent-a-javascript-in-page-gui-agent-that-controls-web-interfaces-with-natural-language-through-the-dom/",
     "MarkTechPost", 8, "2026-07-03", "SEEN", 24,
     "AIエージェント", "agent",
     ["source weight +8", "agent", "model", "multimodal"],
     "Meet Alibaba's Page Agent: A JavaScript In-Page GUI Agent That Controls Web Interfaces With Natural Language Through the DOM."),
    ("The latest AI news we announced in June 2026",
     "https://blog.google/innovation-and-ai/technology/ai/google-ai-updates-june-2026/",
     "Google AI Blog", 16, "2026-07-02", "SEEN", 23,
     "市場動向", "market",
     ["source weight +16", "product/news signal"],
     "The latest AI news we announced in June 2026."),
    ("Building a serverless A2A gateway for agent discovery, routing, and access control",
     "https://aws.amazon.com/blogs/machine-learning/building-a-serverless-a2a-gateway-for-agent-discovery-routing-and-access-control/",
     "AWS Machine Learning Blog", 12, "2026-07-02", "SEEN", 23,
     "AIエージェント、クラウド", "agent",
     ["source weight +12", "agent", "agents"],
     "Building a serverless A2A gateway for agent discovery, routing, and access control."),
    ("AI explained: Why the world needs to act now",
     "https://news.un.org/en/story/2026/07/1167848",
     "UN News", 12, "2026-07-06", "NEW", 54,
     "規制・リスク、市場動向", "risk",
     ["source weight +12", "governance", "policy", "safety", "fresh"],
     "The inaugural UN Global Dialogue on AI Governance opened in Geneva on July 6 with delegates from 169 countries. Secretary-General Antonio Guterres warned that AI is advancing faster than governments can manage, calling for harmonized global rules and an AI safety pledge focused on protecting children."),
    ("Amazon Bedrock AgentCore harness is now generally available: Go from idea to production-grade agent in minutes",
     "https://aws.amazon.com/blogs/machine-learning/amazon-bedrock-agentcore-harness-is-now-generally-available-go-from-idea-to-production-grade-agent-in-minutes/",
     "AWS Machine Learning Blog", 12, "2026-07-06", "NEW", 46,
     "法人導入、AIエージェント、クラウド", "agent",
     ["source weight +12", "agent", "agents", "enterprise", "launch"],
     "Amazon Bedrock AgentCore harness is generally available: define an agent with CreateHarness, run it with InvokeHarness, and get a production-grade agent running in seconds with built-in knowledge, evaluation, and policy controls."),
    ("Tencent releases Hy3 open-source model that allegedly matches models up to five times its active size",
     "https://the-decoder.com/tencent-releases-hy3-open-source-model-that-allegedly-matches-models-up-to-five-times-its-active-size/",
     "The Decoder", 12, "2026-07-06", "NEW", 45,
     "モデル/API、市場動向", "model",
     ["source weight +12", "model", "models", "open source", "fresh"],
     "Tencent released Hy3, a Mixture-of-Experts model with 295 billion total parameters (21 billion active plus a 3.8B MTP layer) and a 256K-token context window. Tencent says it matches the performance of models two to five times its size."),
    ("Zhipu AI launches ZCode to challenge Claude Code and OpenAI Codex at a fraction of the cost",
     "https://the-decoder.com/zhipu-ai-launches-zcode-to-challenge-claude-code-and-openai-codex-at-a-fraction-of-the-cost/",
     "The Decoder", 12, "2026-07-06", "NEW", 44,
     "AIエージェント、市場動向", "agent",
     ["source weight +12", "launch", "agent", "market", "fresh"],
     "China's Zhipu AI launched ZCode, an agentic coding tool positioned against Claude Code and OpenAI Codex at a fraction of the cost, intensifying price competition in AI coding assistants."),
    ("OpenAI models and Codex on Amazon Bedrock are now generally available",
     "https://aws.amazon.com/blogs/machine-learning/openai-models-and-codex-on-amazon-bedrock-are-now-generally-available/",
     "AWS Machine Learning Blog", 12, "2026-07-06", "NEW", 44,
     "法人導入、モデル/API、クラウド", "platform",
     ["source weight +12", "model", "models", "cloud", "enterprise"],
     "GPT-5.5, GPT-5.4, and Codex are now generally available on Amazon Bedrock, giving enterprises a single managed platform for OpenAI models alongside other providers."),
    ("OpenAI's genomics paper accidentally reveals a Pro lineup it hasn't announced yet",
     "https://the-decoder.com/openai-paper-reveals-three-gpt-5-6-pro-models-breaking-with-single-top-tier-strategy/",
     "The Decoder", 12, "2026-07-06", "NEW", 42,
     "モデル/API、研究", "model",
     ["source weight +12", "model", "models", "research", "fresh"],
     "An OpenAI genomics paper inadvertently references three unannounced GPT-5.6 Pro models, suggesting the company is breaking with its single top-tier model strategy."),
    ("Trump drops restrictions on Anthropic's Mythos and Fable models",
     "https://techcrunch.com/2026/06/30/trump-drops-restrictions-on-anthropics-mythos-and-fable-models/",
     "TechCrunch AI", 16, "2026-06-30", "NEW", 41,
     "モデル/API、規制・リスク", "risk",
     ["source weight +16", "model", "models", "risk", "product/news signal"],
     "The Trump administration dropped the export-control restrictions on Anthropic's Mythos and Fable models, clearing the way for their worldwide redeployment on July 1."),
    ("Meituan Releases LongCat-2.0: A 1.6T-Parameter Open MoE Model with Native 1M Context and LongCat Sparse Attention",
     "https://www.marktechpost.com/2026/07/05/meituan-releases-longcat-2-0-a-1-6t-parameter-open-moe-model-with-native-1m-context-and-longcat-sparse-attention/",
     "MarkTechPost", 8, "2026-07-05", "NEW", 41,
     "モデル/API、AIエージェント", "model",
     ["source weight +8", "model", "open source", "agent", "fresh"],
     "Meituan released LongCat-2.0, an open Mixture-of-Experts model with 1.6 trillion total parameters (about 48B active per token), a native 1M-token context window, and a focus on agentic coding workflows."),
    ("Tesla caps employee AI spending at $200 per week",
     "https://the-decoder.com/tesla-caps-employee-ai-spending-at-200-per-week/",
     "The Decoder", 12, "2026-07-06", "NEW", 40,
     "法人導入、市場動向", "market",
     ["source weight +12", "enterprise", "market", "risk", "fresh"],
     "Tesla capped employee AI spending at $200 per week per an internal memo effective July 6 — a data point for how large companies are starting to budget and govern per-employee AI tool usage."),
    ("Deepseek topped Ramp's trending software vendors in June 2026 as US companies chase cheaper AI",
     "https://the-decoder.com/deepseek-topped-ramps-trending-software-vendors-in-june-2026-as-us-companies-chase-cheaper-ai/",
     "The Decoder", 12, "2026-07-06", "NEW", 39,
     "市場動向", "market",
     ["source weight +12", "market", "enterprise", "data", "fresh"],
     "DeepSeek topped Ramp's trending software vendors in June 2026 as US companies chase cheaper AI, another signal that price pressure is reshaping enterprise AI purchasing."),
    ("Build context-rich research agents with Deep Agents and Bedrock AgentCore",
     "https://aws.amazon.com/blogs/machine-learning/build-context-rich-research-agents-with-deep-agents-and-bedrock-agentcore/",
     "AWS Machine Learning Blog", 12, "2026-07-03", "NEW", 39,
     "AIエージェント、クラウド", "agent",
     ["source weight +12", "agent", "agents", "workflow", "data"],
     "How to build context-rich research agents by combining the Deep Agents pattern with Amazon Bedrock AgentCore, covering planning, sub-agents, and grounded retrieval."),
    ("Democratizing business intelligence: BGL's journey with Claude Agent SDK and Amazon Bedrock AgentCore",
     "https://aws.amazon.com/blogs/machine-learning/democratizing-business-intelligence-bgls-journey-with-claude-agent-sdk-and-amazon-bedrock-agentcore/",
     "AWS Machine Learning Blog", 12, "2026-07-02", "NEW", 38,
     "法人導入、AIエージェント", "agent",
     ["source weight +12", "enterprise", "agent", "customer", "data"],
     "A customer case study: BGL democratized business intelligence by building agents with the Claude Agent SDK on Amazon Bedrock AgentCore, letting non-analysts query governed data in natural language."),
    ("Nvidia's Kyber NVL144 reportedly pushed back more than a year, Asian suppliers drop",
     "https://the-decoder.com/nvidias-kyber-nvl144-reportedly-pushed-back-more-than-a-year-asian-suppliers-drop/",
     "The Decoder", 12, "2026-07-06", "NEW", 38,
     "市場動向", "market",
     ["source weight +12", "market", "compute", "fresh"],
     "Nvidia's next AI server system, Kyber NVL144, has reportedly been pushed back to 2028 over circuit-board manufacturing problems, sending shares of Asian suppliers lower."),
    ("ByteDance's Seedance 2.5 breaks the 30-second barrier for AI video generation",
     "https://the-decoder.com/bytedances-seedance-2-5-breaks-the-30-second-barrier-for-ai-video-generation/",
     "The Decoder", 12, "2026-07-05", "NEW", 37,
     "モデル/API、市場動向", "model",
     ["source weight +12", "launch", "multimodal", "fresh"],
     "ByteDance's Seedance 2.5 breaks the 30-second barrier for AI video generation, extending clip length beyond rivals while Hollywood debates the tool's copyright implications."),
    ("AI private schools sell wealthy US families on personalized learning over traditional education",
     "https://the-decoder.com/ai-private-schools-sell-wealthy-us-families-on-personalized-learning-over-traditional-education/",
     "The Decoder", 12, "2026-07-05", "NEW", 34,
     "市場動向", "market",
     ["source weight +12", "market", "fresh", "product/news signal"],
     "AI private schools like Alpha School — two hours of AI tutoring plus project-based workshops for up to $75,000 a year — are selling wealthy US families on personalized learning over traditional education."),
]

SCANNED = 118 + len(ITEMS)
ITEMS.sort(key=lambda it: -it[6])
ITEMS = ITEMS[:40]
NEW_COUNT = sum(1 for it in ITEMS if it[5] == "NEW")

e = html.escape

def angle_text(themes, key):
    return f"注目テーマ: {themes}。{ANGLES[key]}"

def truncate(s, n=260):
    return s if len(s) <= n else s[: n - 3].rstrip() + "..."

# ---- template pieces lifted from the existing report ----------------------
with open(os.path.join(REPO, "latest.html"), encoding="utf-8") as f:
    prev = f.read()
head = prev.split("<body>")[0]  # includes <style> ... </head>

lead = ITEMS[0]

def card(i, it):
    title, url, source, w, date, pill, score, themes, key, signals, summary = it
    pill_cls = "pill pill-new" if pill == "NEW" else "pill pill-neutral"
    sig = " / ".join(signals[:1] + signals[1:5])
    return f"""        <article class="story-card">
          <div class="story-meta">
            <span>No. {i}</span>
            <span>{e(source)}</span>
            <span>{e(date)}</span>
            <span class="{pill_cls}">{pill}</span>
          </div>
          <h3><a href="{e(url)}">{e(localise(title))}</a></h3>
          <p class="original-title">Original: {e(title)}</p>
          <p class="angle">{e(angle_text(themes, key))}</p>
          <p>{e(truncate(summary))}</p>
          <div class="score-row">
            <strong>Score {score}</strong>
            <span>{e(sig)}</span>
          </div>
        </article>
        """

def row(i, it):
    title, url, source, w, date, pill, score, themes, key, signals, summary = it
    return f"""        <tr>
          <td>{i}</td>
          <td><a href="{e(url)}">{e(title)}</a><small>{e(source)} / {e(date)}</small></td>
          <td>{score}</td>
          <td>{e(", ".join(signals))}</td>
        </tr>
        """

theme_counts = {
    "Product and platform launches": sum(1 for it in ITEMS if "launch" in it[9] or "product/news signal" in it[9]),
    "Enterprise adoption and pricing": sum(1 for it in ITEMS if "法人導入" in it[7]),
    "Agents and automation": sum(1 for it in ITEMS if "AIエージェント" in it[7]),
    "Governance and risk": sum(1 for it in ITEMS if "規制・リスク" in it[7]),
}

watch = "\n        \n\n".join(
    f"""        <div class="watch-item">
          <span>{e(k)}</span>
          <strong>{v}</strong>
        </div>"""
    for k, v in theme_counts.items()
)

lt, lu, ls_src, _, ld, _, lscore, lthemes, lkey, _, lsum = lead

body = f"""<body>
  <main class="page">
    <header>
      <div class="kicker">Daily AI Market Brief</div>
      <h1>AI Daily Business Intelligence</h1>
      <p>ビジネス活用に近いAIニュースを、公開情報源から自動収集して優先度順に整理しています。</p>
      <div class="summary-bar">
        <div class="stat"><strong>{SCANNED}</strong><span>Items scanned</span></div>
        <div class="stat"><strong>40</strong><span>Items included</span></div>
        <div class="stat"><strong>{NEW_COUNT}</strong><span>New items</span></div>
        <div class="stat"><strong>{STAMP}</strong><span>Generated JST</span></div>
      </div>
    </header>

        <section class="lead-story">
          <div class="section-label">Top Story</div>
          <h2><a href="{e(lu)}">{e(localise(lt))}</a></h2>
          <p class="original-title">Original: {e(lt)}</p>
          <p class="lead-angle">{e(angle_text(lthemes, lkey))}</p>
          <p>{e(truncate(lsum, 400))}</p>
          <div class="lead-meta">
            <span>{e(ls_src)}</span>
            <span>{e(ld)}</span>
            <span>Score {lscore}</span>
          </div>
        </section>

    <section>
      <h2>Executive Highlights</h2>
      <div class="grid">
{chr(10).join(card(i + 1, it) for i, it in enumerate(ITEMS[:16]))}</div>
    </section>
    <section>
      <h2>Business Priority Watchlist</h2>
      <div class="watchlist">
{watch}</div>
    </section>
    <section>
      <h2>All Ranked Items</h2>
      <table>
        <thead><tr><th>#</th><th>Story</th><th>Score</th><th>Signals</th></tr></thead>
        <tbody>
{chr(10).join(row(i + 1, it) for i, it in enumerate(ITEMS))}</tbody>
      </table>
    </section>

    <section class="next-actions">
      <h2>Suggested Next Actions</h2>
      <p>上位3件を営業・商品企画・開発観点で確認し、今週の提案や実験テーマに落とし込む。</p>
      <p>規制・セキュリティ系の項目が出た場合は、契約書、利用規約、社内AI利用ルールへの影響を確認する。</p>
      <p>APIやエージェント系の発表は、既存業務の自動化候補リストに追加する。</p>
    </section>
  </main>
</body>
</html>
"""

doc = head + body
report_name = f"ai_daily_intel_{FILE_STAMP}.html"
with open(os.path.join(REPO, report_name), "w", encoding="utf-8") as f:
    f.write(doc)
with open(os.path.join(REPO, "latest.html"), "w", encoding="utf-8") as f:
    f.write(doc)

# ---- update index.html -----------------------------------------------------
idx_path = os.path.join(REPO, "index.html")
with open(idx_path, encoding="utf-8") as f:
    idx = f.read()
if report_name not in idx:
    entry = f"""
            <li>
              <a href="{report_name}">{LABEL}</a>
              <span>{STAMP}</span>
            </li>
            """
    idx = idx.replace("<ul>\n      \n", "<ul>\n      " + entry, 1)
    assert report_name in idx
    with open(idx_path, "w", encoding="utf-8") as f:
        f.write(idx)
    print("index: added entry", report_name)
else:
    print("index: entry already present, left unchanged")

print("report:", report_name)
print("generated:", STAMP, "JST | new items:", NEW_COUNT)
print("watchlist:", theme_counts)
if MISSING_JA:
    print("\nWARNING: missing Japanese titles for", len(MISSING_JA), "items:")
    for t in MISSING_JA:
        print("  -", t)
