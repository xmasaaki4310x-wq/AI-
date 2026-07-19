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
    "OpenAI's GPT-5.6 Sol, Terra, and Luna and xAI's Grok 4.5 launch on the same day for the first time in AI history":
        "OpenAIのGPT-5.6(Sol/Terra/Luna)とxAIのGrok 4.5が史上初の同日ローンチ",
    "Meta enters the crowded AI coding battle with Muse Spark 1.1":
        "Meta、「Muse Spark 1.1」で混戦のAIコーディング競争に参入",
    "Meta's Muse Spark 1.1 API pricing squeezes OpenAI and Anthropic as the AI price war heats up":
        "MetaのMuse Spark 1.1、破格のAPI価格でOpenAI・Anthropicを圧迫—AI価格競争が激化",
    "Grok 4.5 is so cheap compared to Fable 5 and GPT 5.5 that benchmark gaps may not matter much":
        "Grok 4.5、Fable 5やGPT-5.5と比べ破格の安さでベンチマーク差が霞む可能性",
    "OpenAI pairs its GPT-5.6 public rollout with ChatGPT Work, a new agent that handles entire workflows":
        "OpenAI、GPT-5.6の一般提供と同時に業務全体を任せる新エージェント「ChatGPT Work」を投入",
    "SpaceXAI Releases Grok 4.5, a Cursor-Trained Model for Coding, Agentic Tasks, and Knowledge Work at $2/M Input":
        "SpaceXAI、CursorデータでトレーニングしたGrok 4.5を公開—コーディング・エージェント業務向けに入力$2/M",
    "Meta Superintelligence Labs Releases Muse Spark 1.1: A Multimodal Reasoning Model for Agentic Tasks on Meta Model API":
        "Meta Superintelligence Labs、Meta Model API上でマルチモーダル推論モデル「Muse Spark 1.1」を公開",
    "OpenAI's AI beats every human at AtCoder, a top competitive programming contest":
        "OpenAIのAI、トップ競技プログラミング大会AtCoderで全人類選手に勝利",
    "OpenAI finds roughly 30 percent of popular AI coding test is broken":
        "OpenAI、人気のAIコーディングベンチマークの約3割に欠陥があると指摘し支持撤回",
    "China forces its biggest AI platforms to shut down humanlike chatbot personas":
        "中国政府、大手AIプラットフォームに人間そっくりなチャットボット人格の停止を強制",
    "OpenAI and Anthropic are giving away millions in computing power to attract startups":
        "OpenAIとAnthropic、スタートアップ獲得のため数百万ドル分の計算資源を無償提供",
    "Popular open source AI developer tool Ollama raises $65M, grows to nearly 9M users":
        "オープンソースAI開発ツールOllama、6,500万ドル調達—月間利用者は900万人近くに",
    "Can AI answer the $3 trillion question?":
        "AIは「3兆ドルの問い」に答えられるか—2026年のAIインフラ投資は回収できるのか",
    "Google will now disclose which ads are made with AI":
        "Google、AIで作られた広告であることを開示する新機能を導入",
    "DeepSeek's confirmed inference chip project sent Nvidia shares modestly lower":
        "DeepSeekの推論チップ開発計画が明らかに、NVIDIA株が小幅下落",
    "Anthropic invites hard questions about AI and pledges to track its response to them":
        "Anthropic、AIに関する「厳しい問い」を募集し、対応状況を公開追跡すると表明",
    "Ben Bernanke appointed to Anthropic's Long-Term Benefit Trust":
        "元FRB議長ベン・バーナンキ氏、Anthropicの長期便益トラストに就任",
    "SK Hynix raises $26.5B in the biggest foreign IPO in US history, is urged to build new US fabs":
        "SKハイニックス、米国史上最大の外国企業IPOで265億ドル調達—米国内工場の新設を求められる",
    "OpenAI's GPT-5.6 Sol autonomously post-trained the smaller Luna model with a \"fairly underspecified prompt\"":
        "OpenAIのGPT-5.6 Sol、「かなり大雑把な指示」だけで小型モデルLunaの事後学習を自律実行",
    "China softens stance on Nvidia AI chips, to allow Alibaba, ByteDance, and DeepSeek to buy H200s":
        "中国、NVIDIA AIチップへの姿勢を軟化—Alibaba・ByteDance・DeepSeekにH200購入を一部容認",
    "Doubao and Qwen pull humanlike agent personas offline following Chinese regulatory order":
        "中国当局の指示を受けDoubaoとQwenが人間的なエージェント人格機能を停止へ",
    "The Fed wants AI investor Marc Andreessen to help figure out if AI can tame inflation":
        "FRB、AI投資家マーク・アンドリーセン氏を招き「AIはインフレを抑えられるか」を検討する作業部会を設置",
    "Accenture and AWS launch agentic AI solutions to close the enterprise data readiness gap":
        "AccentureとAWS、企業データの準備不足を解消するエージェント型AIソリューションを提供開始",
    "Google Cloud launches Agent Marketplace with more than 70 pre-built agents from partners":
        "Google Cloud、Accenture・Adobe・Atlassianなどパートナー製70以上の構築済みエージェントを揃えた「Agent Marketplace」を開設",
    "Apple sues OpenAI for allegedly running a \"coordinated campaign\" to steal trade secrets through poached employees":
        "Apple、従業員引き抜きによる「組織的な企業秘密窃取キャンペーン」でOpenAIを提訴",
    "JADEPUFFER: the first documented end-to-end autonomous AI ransomware attack":
        "JADEPUFFER:初めて確認された完全自律型AIランサムウェア攻撃、Sysdigが全容解析",
    "Chinese AI models now account for 30 to 46 percent of US enterprise token usage on developer platforms":
        "中国製AIモデル、米企業の開発者プラットフォーム利用トークンの30〜46%を占有—CNBC調査",
    "OpenAI admits it \"didn't get everything quite right\" with ChatGPT Work launch and scrambles to fix UX and costs":
        "OpenAI、ChatGPT Work発売で「すべてがうまくいったわけではない」と認め、UXとコストの修正に追われる",
    "Meta's Muse Spark 1.1 edges ahead of GLM 5.2 in coding while undercutting it on price":
        "MetaのMuse Spark 1.1、コーディング性能でGLM 5.2をわずかに上回りつつ価格でも下回る",
    "Bun ditches Zig for Rust with help from Claude Fable 5, writes over a million lines of code in 11 days":
        "Bun、Claude Fable 5の支援でZigからRustへ全面移行—11日間で100万行超のコードを書き上げる",
    "Tencent in talks to acquire majority stake in Manus after Meta unwinds its China-blocked deal":
        "Tencent、Meta撤退後のManusに過半数出資を協議—北京当局の介入で中国資産の巻き戻しが完了",
    "Three humanoid robotics companies move toward public markets in the same week":
        "ヒューマノイドロボット3社が同じ週に相次いで上場準備—Agility SPAC申請、Unitreeが上海IPO通過、TeslaはOptimus専用工場に転換",
    "Anthropic's annualized revenue overtakes OpenAI's, fueled by AI coding tools":
        "Anthropicの年換算売上高がOpenAIを逆転—コーディング向けAIツールが牽引",
    "SambaNova raises $1B Series F at $11B valuation, lands JPMorgan Chase as inference partner":
        "AIチップのSambaNova、11億ドル評価額で10億ドルのシリーズFを調達—JPMorgan Chaseを推論パートナーに獲得",
    "Gemini 3.5 Pro targets a July 17 launch with a 2M-token context window and new Deep Think reasoning mode":
        "Gemini 3.5 Pro、200万トークン文脈と新推論モード「Deep Think」搭載で7月17日ローンチ予定と判明",
    "ByteDance and Alibaba shut down AI companion persona features following Chinese regulatory order":
        "ByteDanceとAlibaba、中国当局の規制を受けAIコンパニオンの人格機能を停止へ",
    "Amazon sunsets Mechanical Turk, the original \"artificial artificial intelligence\"":
        "Amazon、「人工的な人工知能」の元祖Mechanical Turkのサービスを終了",
    "Guide to Loop Engineering: How autoresearch and Bilevel Autoresearch turn AI agents into autonomous ML research loops":
        "ループエンジニアリング入門:「autoresearch」と「Bilevel Autoresearch」がAIエージェントを自律的な機械学習研究ループに変える仕組み",
    "Satya Nadella has issued a shocking warning to companies using AI":
        "サティア・ナデラCEO、AIを利用する企業に衝撃的な警告—「情報を消費すれば、その情報を作り出したことになる」",
    "Sam Altman's space data center trash talk is what most experts already believe":
        "サム・アルトマン氏の「宇宙データセンター」批判は専門家の間ではすでに定説—イーロン・マスク氏と応酬",
    "OpenAI's new prompting guide tells users to stop overthinking and start with the result":
        "OpenAIの新プロンプトガイド、「考えすぎず、まず結果から始めよ」と一般ユーザーに助言",
    "Copilot goes cheap as Microsoft phases out OpenAI and Anthropic models to cut costs":
        "Microsoft、コスト削減のためCopilotからOpenAI・Anthropicモデルを段階的に排除し低価格化",
    "Stanford Researchers Introduce TRACE: A Capability-Targeted Agentic Training System That Turns Recurrent Agent Failures Into Synthetic RL Environment":
        "スタンフォード大学、エージェントの再発する失敗パターンを合成RL環境に変換する能力特化型訓練システム「TRACE」を発表",
    "Skyfall AI Releases MORPHEUS: A Persistent Enterprise Simulation Benchmark That Makes Continual Reinforcement Learning Necessary Under Structured Non-Stationarity":
        "Skyfall AI、実運用同様に環境が変化し続ける企業シミュレーションベンチマーク「MORPHEUS」を公開—継続的強化学習を必須に",
    "Prime Intellect Releases Verifiers v1: Composable Tasksets, Harnesses, and Runtimes for Agentic RL Training and Evaluations":
        "Prime Intellect、エージェント型RLの訓練・評価向け「Verifiers v1」を公開—組み合わせ可能なタスクセット・ハーネス・ランタイムを提供",
    "Xi Jinping to deliver keynote at Shanghai's World AI Conference for the first time, as Gemini 3.5 Pro launch looms on the same day":
        "習近平氏、上海の世界AI大会で初の基調講演—同日にGemini 3.5 Proのローンチも見込まれ「AI最大の一日」に",
    "The real AI race may no longer be at the frontier as Chinese open-weight models surpass US models on Hugging Face downloads":
        "「真のAI競争はもはや最先端モデルではない」—中国製オープンウェイトモデルがHugging Faceダウンロード数で米国製を上回る",
    "Anthropic adds public sharing and multiplayer editing to Artifacts, plus creation via Claude Tag from Slack":
        "Anthropic、Artifactsに公開共有と複数人同時編集を追加、Slackの「Claude Tag」からの直接作成にも対応",
    "Reflection inks $1B compute deal with Nebius":
        "オープンモデル開発のReflection AI、Nebiusと10億ドル規模の計算資源契約を締結",
    "OpenAI pushes back on Apple trade secret lawsuit":
        "OpenAI、Appleの企業秘密訴訟に「根拠が薄い」と反論",
    "DeepSeek reportedly in talks to raise $1.5B, then IPO":
        "DeepSeek、15億ドル規模の資金調達後にIPOを目指すと報道—評価額は約710億ドル",
    "Anthropic's newest ad is creeping people out":
        "Anthropicの最新広告「厳しい問いにこそ希望がある」、不気味な演出が視聴者をざわつかせる",
    "Spotify expands its AI push with a ChatGPT-like music assistant":
        "Spotify、ChatGPT風の音楽アシスタントでAI活用を拡大",
    "PixVerse's $2B valuation shows investors still believe AI video generation has room for another winner":
        "AI動画生成のPixVerse、評価額20億ドルに—投資家はまだ「次の勝者」の余地を信じている",
    "Deepmind CEO Hassabis says \"nobody in the world knows what happens next\" so \"cautious optimism\" means building guardrails now":
        "DeepMindのハサビスCEO「この先何が起きるか世界の誰も分からない」—「慎重な楽観」とは今のうちにガードレールを築くこと",
    "Mistral Vibe for Code vs Claude Code vs Cursor vs Codex: Four Agents Scored on One Scaffold-to-PR Task":
        "Mistral Vibe for Code対Claude Code対Cursor対Codex:4つのコーディングエージェントを同一タスクで採点比較",
    "Thinking Machines amps up its bet against one-size-fits-all AI with its first open model, Inkling":
        "Thinking Machines、「画一的なAI」への対抗策として初の自社オープンモデル「Inkling」を公開",
    "Anthropic, Blackstone bet the next trillion-dollar AI business is implementation, not just models":
        "AnthropicとBlackstone、「次の兆ドル市場はモデルではなく導入支援」に賭け合弁会社Odeを設立",
    "Indian AI coding startup Emergent becomes a unicorn with $130M Series C":
        "インドのAIコーディングスタートアップEmergent、1.3億ドルのシリーズCでユニコーンに",
    "Microsoft patches record number of security vulnerabilities, citing its use of AI":
        "Microsoft、AI活用を理由に過去最多件数のセキュリティ脆弱性を一斉修正",
    "Apple Intelligence approved for launch in China with Alibaba's Qwen AI":
        "Apple Intelligence、AlibabaのQwenと組み合わせて中国での提供が承認される",
    "Hack suggests AI music generator Suno scraped YouTube for training data":
        "ハッキングにより、AI音楽生成ツールSunoがYouTubeを無断学習データにしていた疑いが浮上",
    "OpenAI's first hardware product is a screenless AI speaker designed to feel alive":
        "OpenAI初のハードウェア製品は「生きているように感じる」画面なしAIスピーカー",
    "OpenAI's Codex now encrypts instructions between AI agents, leaving developers blind to internal delegation":
        "OpenAIのCodex、エージェント間の指示を暗号化—開発者は内部の委任処理を追跡できなくなる",
    "German AI consortium releases Soofi S, an open 30B model that tops benchmarks in both English and German":
        "ドイツのAIコンソーシアム、英独両言語のベンチマークで首位の300億パラメータ級オープンモデル「Soofi S」を公開",
    "GPT-5.6 Sol reportedly disproves a 30-year-old statistics conjecture in 90 minutes after humans couldn't crack it":
        "GPT-5.6 Sol、人類が解けなかった30年来の統計学の予想を90分で反証したと報告",
    "Google Releases LiteRT.js: A JavaScript Binding of LiteRT That Runs .tflite Models in Browsers via WebGPU":
        "Google、WebGPU経由でブラウザ上に.tfliteモデルを実行する「LiteRT.js」を公開",
    "Kimi's open model K3 nears GPT-5.6 Sol and Fable 5 while signaling the end of super cheap Chinese AI":
        "Kimiのオープンモデル「K3」がGPT-5.6 SolやFable 5に接近—「激安中国AI」時代の終わりを予感させる",
    "xAI open-sources \"Grok-Build\" on GitHub after massive data breach":
        "xAI、大規模データ流出を受けコーディングエージェント「Grok-Build」をGitHubでオープンソース化",
    "OpenAI wants developers to stop typing commands and start using a joystick to control their AI agents":
        "OpenAI、開発者に「コマンド入力」をやめさせジョイスティックでAIエージェントを操作させたい—専用ハード「Codex Micro」発表",
    "Anthropic extends free Fable 5 access for subscribers as OpenAI's GPT-5.6 Sol heats up the pricing war":
        "Anthropic、OpenAIのGPT-5.6 Solが激化させる価格競争を受け、サブスク会員向けFable 5無料利用枠を延長",
    "AI-powered travel agency Fora hits unicorn status, raises $60M":
        "AI活用の旅行代理店Fora、6,000万ドル調達でユニコーンに",
    "Microsoft July 2026 Patch Tuesday fixes record 570 flaws as AI-powered scanning finds bugs before attackers do":
        "Microsoft、AI活用の脆弱性スキャンで攻撃者より先にバグを発見—2026年7月分は過去最多570件を一斉修正",
    "TSMC posts record quarter as AI chip demand pushes full-year growth outlook past 40%":
        "TSMC、AIチップ需要により四半期最高益を記録—通期成長見通しを40%超に上方修正",
    "Gemini 3.5: frontier intelligence with action":
        "Google、「Gemini 3.5」を発表—200万トークン文脈と新推論モード「Deep Think」を備えたフロンティアモデル",
    "China's Xi says AI 'should not be a solo performance by a single country'":
        "習近平氏、世界AI大会で「AIは一国だけの独奏であってはならない」と発言—国際協調を呼びかけ",
    "Just like Deepseek, China's Kimi K3 is forcing Western AI labs to question their compute advantage":
        "DeepSeekに続きKimi K3も、西側AI研究所に「計算資源の優位性」への疑問を突きつける",
    "Netflix's 300 AI productions show how fast the technology is spreading through entertainment":
        "Netflix、AI活用作品が300本に—エンタメ業界への技術浸透の速さを示す",
    "OpenAI Details GPT-Red: An Internal Automated Red-Teaming Model That Beat Human Red-Teamers 84% To 13% On Prompt Injection":
        "OpenAI、社内向け自動レッドチーミングモデル「GPT-Red」を詳細公開—プロンプトインジェクション検出で人間のレッドチームに84%対13%で勝利",
    "NVIDIA AI Releases Nemotron 3 Embed: An Open Embedding Collection Whose 8B Checkpoint Ranks #1 on RTEB":
        "NVIDIA、オープンな埋め込みモデル群「Nemotron 3 Embed」を公開—80億パラメータ版がRTEBで首位に",
    "Anthropic slashes Claude Fable 5 limits in Max and Team Premium and pushes Pro users toward API pricing":
        "Anthropic、Max・Team PremiumでのFable 5利用上限を大幅削減、Proユーザーは実質API課金へ誘導",
    "China's Xi Jinping launches new AI alliance: What is it?":
        "習近平氏が新たなAI連合を発足—「世界AI協力機構」とは何か",
    "We Just Had The First Humanoid Robot Strike Ever":
        "史上初の「ヒューマノイドロボット・ストライキ」が発生—Hyundai労組がAtlas導入への懸念からボーナス・雇用保障を要求",
    "Google Cloud's Always-On Memory Agent Replaces RAG and Embeddings With Continuous LLM Consolidation on Gemini 3.1 Flash-Lite":
        "Google Cloud、RAGと埋め込みを置き換える「常時稼働メモリエージェント」を公開—Gemini 3.1 Flash-Liteで継続的にLLMが記憶を統合",
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
     "Anthropic News", 20, "date unknown", "SEEN", 19,
     "モデル/API、規制・リスク", "risk",
     ["source weight +20", "launch", "model", "security", "product/news signal"],
     "As of June 30, 2026, the US export controls on Fable 5 and Mythos 5 have been lifted. Fable 5 returned to users worldwide on July 1 across the Claude Platform, Claude.ai, Claude Code, and Claude Cowork, together with a new cybersecurity classifier and an industry framework for assessing jailbreak severity developed with Amazon, Microsoft, and Google."),
    ("Meet WebBrain: An Open-Source, Local-First AI Browser Agent That Reads Pages and Automates Tasks in Chrome and Firefox",
     "https://www.marktechpost.com/2026/07/02/meet-webbrain-an-open-source-local-first-ai-browser-agent-that-reads-pages-and-automates-tasks-in-chrome-and-firefox/",
     "MarkTechPost", 8, "2026-07-03", "SEEN", 13,
     "AIエージェント、モデル/API、クラウド、規制・リスク", "privacy",
     ["source weight +8", "privacy", "api", "agent", "model"],
     "WebBrain is a free, MIT-licensed AI browser agent for Chrome and Firefox. It reads pages, extracts data, and automates multi-step tasks through Ask and Act modes. Run it on local models like llama.cpp or Ollama for privacy, or connect any cloud API."),
    ("UK's AI Security Institute finds standard benchmarks systematically underestimate what AI agents can actually do",
     "https://the-decoder.com/uks-ai-security-institute-finds-standard-benchmarks-systematically-underestimate-what-ai-agents-can-actually-do/",
     "The Decoder", 12, "2026-07-04", "SEEN", 12,
     "AIエージェント、モデル/API、規制・リスク、研究", "risk",
     ["source weight +12", "security", "agent", "agents", "model"],
     "In a study covering seven benchmarks, the UK's AI Security Institute shows that standard AI evaluations systematically underestimate agent capabilities by capping the compute budget. On software engineering tasks, success rates jumped about 25 percent when the cap was lifted."),
    ("Anthropic invests $100 million into the Claude Partner Network",
     "https://www.anthropic.com/news/claude-partner-network",
     "Anthropic News", 20, "date unknown", "SEEN", 12,
     "法人導入、買収・提携", "partner",
     ["source weight +20", "partnership", "partners", "enterprise", "product/news signal"],
     "Anthropic is investing $100 million into the Claude Partner Network to accelerate enterprise deployments through consultancies, system integrators, and cloud marketplaces."),
    ("Introducing Web Search on Amazon Bedrock AgentCore",
     "https://aws.amazon.com/blogs/machine-learning/introducing-web-search-on-amazon-bedrock-agentcore/",
     "AWS Machine Learning Blog", 12, "2026-07-03", "SEEN", 11,
     "法人導入、AIエージェント、クラウド", "agent",
     ["source weight +12", "agent", "agents", "search", "enterprise"],
     "AWS announced general availability of Web Search on Amazon Bedrock AgentCore, a fully managed MCP tool that grounds agent responses in current, cited web knowledge with zero data egress from the customer's AWS environment, built on Amazon's own search infrastructure."),
    ("New Claude Mythos becomes the first AI model to clear all cyberattack simulations from Britain's AI safety agency",
     "https://the-decoder.com/new-claude-mythos-becomes-the-first-ai-model-to-clear-all-cyberattack-simulations-from-britains-ai-safety-agency/",
     "The Decoder", 12, "2026-07-05", "SEEN", 10,
     "モデル/API、規制・リスク、研究", "risk",
     ["source weight +12", "security", "model", "benchmark", "fresh"],
     "Claude Mythos is the first AI model to clear every cyberattack simulation run by Britain's AI safety agency, a milestone for capability evaluations that also sharpens the debate over how dual-use skills should be gated and monitored."),
    ("Alibaba reportedly bans employees from using Claude Code",
     "https://techcrunch.com/2026/07/04/alibaba-reportedly-bans-employees-from-using-claude-code/",
     "TechCrunch AI", 16, "2026-07-04", "SEEN", 9,
     "法人導入、市場動向、規制・リスク", "market",
     ["source weight +16", "enterprise", "risk", "fresh", "product/news signal"],
     "China's Alibaba will ban employees from using Anthropic's programming tool Claude Code starting July 10. Anthropic already prohibits Chinese companies and their foreign subsidiaries from using its models and has been closing loopholes that allowed access."),
    ("Anthropic's Fable 5 is back worldwide after a two-week government ban over a jailbreak",
     "https://the-decoder.com/anthropics-fable-5-is-back-worldwide-after-a-two-week-government-ban-over-a-jailbreak/",
     "The Decoder", 12, "2026-07-04", "SEEN", 8,
     "モデル/API、規制・リスク", "risk",
     ["source weight +12", "security", "model", "risk", "fresh"],
     "Fable 5 is available worldwide again after the US Department of Commerce lifted the export controls imposed on June 12 over a jailbreak incident. Anthropic redeployed the model on July 1 with an additional cybersecurity classifier in place."),
    ("Expanding our use of Google Cloud TPUs and Services",
     "https://www.anthropic.com/news/expanding-our-use-of-google-cloud-tpus-and-services",
     "Anthropic News", 20, "date unknown", "SEEN", 8,
     "クラウド、買収・提携", "partner",
     ["source weight +20", "cloud", "partnership", "product/news signal"],
     "Anthropic is expanding its use of Google Cloud TPUs and services to scale training and inference capacity, deepening the compute partnership behind the Claude model family."),
    ("Agent-guided workflows to accelerate model customization in Amazon SageMaker AI",
     "https://aws.amazon.com/blogs/machine-learning/agent-guided-workflows-to-accelerate-model-customization-in-amazon-sagemaker-ai/",
     "AWS Machine Learning Blog", 12, "2026-07-03", "SEEN", 7,
     "AIエージェント、モデル/API、クラウド", "platform",
     ["source weight +12", "agent", "workflow", "model", "cloud"],
     "Amazon SageMaker AI now offers an agentic experience where developers describe their use case in natural language and an AI coding agent streamlines the journey from data preparation through technique selection, evaluation, and deployment."),
    ("Anthropic Launches Claude Science Beta: A Multi-Agent AI Workbench for Reproducible Genomics, Proteomics, and Cheminformatics Pipelines",
     "https://www.marktechpost.com/2026/07/04/anthropic-launches-claude-science-beta/",
     "MarkTechPost", 8, "2026-07-05", "SEEN", 7,
     "AIエージェント、モデル/API", "agent",
     ["source weight +8", "launch", "agent", "model", "models"],
     "Anthropic released Claude Science in beta on June 30, 2026. The app runs on existing Claude models. A coordinating agent delegates to domain specialists, a reviewer agent flags and corrects citations and numbers, and every figure ships with its exact code and environment."),
    ("Microsoft follows Anthropic and OpenAI into the AI super app race with overhauled Copilot and AutoPilot agents",
     "https://the-decoder.com/microsoft-follows-anthropic-and-openai-into-the-ai-super-app-race-with-overhauled-copilot-and-autopilot-agents/",
     "The Decoder", 12, "2026-07-04", "SEEN", 6,
     "法人導入、AIエージェント", "agent",
     ["source weight +12", "enterprise", "agent", "agents", "copilot"],
     "Microsoft reportedly plans to merge its consumer and enterprise Copilot apps into a single app in August. Rarely used features like Copilot Podcasts are getting cut, and new AI agents called \"AutoPilot\" will handle tasks in the background for an extra fee."),
    ("OpenAI and Broadcom unveil \"Jalapeño,\" a custom chip built for LLM inference",
     "https://the-decoder.com/openai-and-broadcom-unveil-jalapeno-a-custom-chip-built-for-llm-inference/",
     "The Decoder", 12, "2026-07-05", "SEEN", 6,
     "買収・提携、市場動向", "partner",
     ["source weight +12", "partnership", "inference", "model", "fresh"],
     "OpenAI and Broadcom unveiled Jalapeño, a custom accelerator designed specifically for large language model inference, the first tangible product of their multi-year chip co-development deal."),
    ("Anthropic Redeploys Claude Fable 5 on July 1 After US Export Controls Lift, Adds New Cybersecurity Classifier",
     "https://www.marktechpost.com/2026/07/01/anthropic-redeploys-claude-fable-5-on-july-1-after-us-export-controls-lift-adds-new-cybersecurity-classifier/",
     "MarkTechPost", 8, "2026-07-01", "SEEN", 6,
     "モデル/API、規制・リスク", "risk",
     ["source weight +8", "security", "launch", "model", "deployment"],
     "Anthropic redeployed Claude Fable 5 on July 1 after the US Department of Commerce lifted export controls. The rollout adds a new cybersecurity classifier and ships alongside a cross-industry framework for scoring jailbreak severity."),
    ("New in Amazon Bedrock AgentCore: Build agents with broader knowledge and continuous learning",
     "https://aws.amazon.com/blogs/machine-learning/new-in-amazon-bedrock-agentcore-build-agents-with-broader-knowledge-and-continuous-learning/",
     "AWS Machine Learning Blog", 12, "2026-07-02", "SEEN", 5,
     "法人導入、AIエージェント、クラウド", "agent",
     ["source weight +12", "agent", "agents", "enterprise", "data"],
     "Amazon Bedrock AgentCore adds broader knowledge grounding and continuous learning so deployed agents can keep improving from operational feedback while meeting enterprise governance requirements."),
    ("Get started with the Claude apps gateway for Google Cloud",
     "https://cloud.google.com/blog/topics/developers-practitioners/announcing-claude-apps-gateway-for-google-cloud/",
     "Google Cloud AI & ML", 12, "2026-07-02", "SEEN", 5,
     "法人導入、AIエージェント、モデル/API、クラウド", "agent",
     ["source weight +12", "enterprise", "platform", "agent", "cloud"],
     "Anthropic's agentic coding tool Claude Code has worked with Google Cloud for a while now. An individual developer could easily point CLAUDE_CODE_USE_VERTEX=1 at a Google Cloud (GCP) project, grant the role roles/aiplatform.user, and inference stays inside your project."),
    ("LlamaIndex 'legal-kb': Agentic Retrieval over Index v2 with retrieve, find, read, and grep Tools",
     "https://www.marktechpost.com/2026/07/05/llamaindex-legal-kb-agentic-retrieval-over-index-v2-with-retrieve-find-read-and-grep-tools/",
     "MarkTechPost", 8, "2026-07-05", "SEEN", 4,
     "AIエージェント、モデル/API", "agent",
     ["source weight +8", "agent", "api", "workflow", "fresh"],
     "LlamaIndex released legal-kb, a reference app exposing Index v2 retrieval as agent tools: retrieve, find, read, and grep. It shows how agentic retrieval patterns replace one-shot RAG pipelines for legal knowledge bases."),
    ("New data from OpenAI and Anthropic show how people actually use ChatGPT and Claude",
     "https://the-decoder.com/new-data-from-openai-and-anthropic-show-how-people-actually-use-chatgpt-and-claude/",
     "The Decoder", 12, "2026-07-05", "SEEN", 4,
     "市場動向、研究", "market",
     ["source weight +12", "data", "market", "model", "fresh"],
     "New usage studies from OpenAI and Anthropic detail how people actually use ChatGPT and Claude, giving planners real-world category splits between work tasks, coding, writing, and personal use."),
    ("Microsoft launches its own AI deployment company with $2.5 billion commitment",
     "https://techcrunch.com/2026/07/02/microsoft-launches-its-own-ai-deployment-company-with-2-5-billion-commitment/",
     "TechCrunch AI", 16, "2026-07-02", "SEEN", 4,
     "法人導入", "platform",
     ["source weight +16", "launch", "deployment", "product/news signal"],
     "Microsoft follows Amazon, OpenAI, and Anthropic with its new AI deployment group."),
    ("Cloudflare's new policy pushes AI companies to pay for publishers' content",
     "https://techcrunch.com/2026/07/01/cloudflares-new-policy-pushes-ai-companies-to-pay-for-publishers-content/",
     "TechCrunch AI", 16, "2026-07-02", "SEEN", 4,
     "AIエージェント、クラウド、規制・リスク", "agent",
     ["source weight +16", "agent", "agents", "cloud", "search"],
     "Cloudflare is giving AI companies until September 15 to separate web crawlers used for search from those used for AI training and agents, or risk being blocked by default on many publisher sites."),
    ("AI industry finds its 2026 narrative as OpenAI and Microsoft argue users are the bottleneck, not models",
     "https://the-decoder.com/ai-industry-finds-its-2026-narrative-as-openai-and-microsoft-argue-users-are-the-bottleneck-not-models/",
     "The Decoder", 12, "2026-07-05", "SEEN", 4,
     "市場動向", "market",
     ["source weight +12", "market", "model", "models", "fresh"],
     "OpenAI and Microsoft executives are converging on a new 2026 narrative: model capability is no longer the constraint on value — user adoption, workflow redesign, and organizational change are."),
    ("Anthropic opens Seoul office and announces new partnerships across the Korean AI ecosystem",
     "https://www.anthropic.com/news/seoul-office-partnerships-korean-ai-ecosystem",
     "Anthropic News", 20, "date unknown", "SEEN", 4,
     "買収・提携", "partner",
     ["source weight +20", "partnership", "partners", "product/news signal"],
     "Anthropic opens Seoul office and announces new partnerships across the Korean AI ecosystem"),
    ("Efficiently serve dozens of fine-tuned models with vLLM on Amazon SageMaker AI and Amazon Bedrock",
     "https://aws.amazon.com/blogs/machine-learning/efficiently-serve-dozens-of-fine-tuned-models-with-vllm-on-amazon-sagemaker-ai-and-amazon-bedrock/",
     "AWS Machine Learning Blog", 12, "2026-07-02", "SEEN", 4,
     "モデル/API、クラウド", "platform",
     ["source weight +12", "model", "models", "inference", "cloud"],
     "This post shows how to serve dozens of fine-tuned model variants efficiently with vLLM multi-LoRA serving on Amazon SageMaker AI and Amazon Bedrock, cutting idle GPU cost while keeping per-tenant isolation."),
    ("Stanford's AI Index 2026 shows rapid progress, growing safety concerns, and declining public trust",
     "https://the-decoder.com/stanfords-ai-index-2026-shows-rapid-progress-growing-safety-concerns-and-declining-public-trust/",
     "The Decoder", 12, "2026-07-04", "SEEN", 4,
     "研究、規制・リスク、市場動向", "market",
     ["source weight +12", "research", "safety", "data", "fresh"],
     "Stanford's AI Index 2026 documents rapid capability progress alongside growing safety concerns and declining public trust, a mix that shapes how enterprise buyers and regulators approach AI adoption this year."),
    ("What is Mistral AI? Everything to know about the OpenAI competitor",
     "https://techcrunch.com/2026/07/04/what-is-mistral-ai-everything-to-know-about-the-openai-competitor/",
     "TechCrunch AI", 16, "2026-07-05", "SEEN", 4,
     "モデル/API、資金調達", "model",
     ["source weight +16", "funding", "model", "models", "open source"],
     "Mistral AI, which offers some open source AI models, has raised significant funding since its creation in 2023, with the ambition to \"put frontier AI in the hands of everyone.\" A new open-weight model is planned for this summer with early access in July."),
    ("Mistral AI Releases Leanstral 1.5: An Apache-2.0 Lean 4 Code Agent Model Solving 587 of 672 PutnamBench Problems",
     "https://www.marktechpost.com/2026/07/03/mistral-ai-releases-leanstral-1-5-an-apache-2-0-lean-4-code-agent-model-solving-587-of-672-putnambench-problems/",
     "MarkTechPost", 8, "2026-07-04", "SEEN", 4,
     "法人導入、AIエージェント、モデル/API、研究", "agent",
     ["source weight +8", "agent", "model", "benchmark", "deployment"],
     "Mistral AI released Leanstral 1.5, a free Apache-2.0 code agent model for Lean 4. It saturates miniF2F and solves 587 of 672 PutnamBench problems. The 119B mixture-of-experts activates 6.5B parameters per token."),
    ("AlloyDB AI Functions - now with revolutionary performance boosts and cost savings",
     "https://cloud.google.com/blog/products/databases/boost-performance-and-lower-costs-with-alloydb-ai-functions/",
     "Google Cloud AI & ML", 12, "2026-07-02", "SEEN", 4,
     "AIエージェント、モデル/API", "platform",
     ["source weight +12", "agent", "agents", "model", "search"],
     "AlloyDB is an AI-native database—it isn't just a passive data store, it intelligently understands and processes your data. With AlloyDB, you get industry-leading vector and hybrid search, and near 100% accurate natural language-to-SQL capabilities."),
    ("Safely Releasing Frontier Models to Customers",
     "https://aws.amazon.com/blogs/machine-learning/safely-releasing-frontier-models-to-customers/",
     "AWS Machine Learning Blog", 12, "2026-07-01", "SEEN", 4,
     "法人導入、モデル/API、クラウド、規制・リスク", "risk",
     ["source weight +12", "customer", "customers", "security", "model"],
     "It's our goal for AWS to be the most secure place to run any workload, and in support of that we've been deeply investing in security across our services since AWS's inception more than two decades ago. Our AI services like Amazon Bedrock are built on this foundation."),
    ("Simplify model selection in Amazon Bedrock with the open source Model Profiler",
     "https://aws.amazon.com/blogs/machine-learning/simplify-model-selection-in-amazon-bedrock-with-the-open-source-model-profiler/",
     "AWS Machine Learning Blog", 12, "2026-07-02", "SEEN", 4,
     "モデル/API、クラウド", "platform",
     ["source weight +12", "api", "model", "open source", "search"],
     "The Amazon Bedrock Model Profiler is an open source tool that aggregates model metadata from multiple AWS APIs and external sources into a single, searchable interface."),
    ("OpenAI cofounder envisions \"almost no interface\" future where nobody learns software anymore",
     "https://the-decoder.com/openai-cofounder-envisions-almost-no-interface-future-where-nobody-learns-software-anymore/",
     "The Decoder", 12, "2026-07-04", "SEEN", 4,
     "AIエージェント、モデル/API", "agent",
     ["source weight +12", "agent", "market", "model", "models"],
     "Greg Brockman admits ChatGPT's plugins, heavily marketed in 2023, failed \"because the models weren't ready.\" Instead of app extensions, he sees the future in an invisible, context-aware agent."),
    ("Security vulnerability reports have exploded since AI models started hunting for bugs",
     "https://the-decoder.com/security-vulnerability-reports-have-exploded-since-ai-models-started-hunting-for-bugs/",
     "The Decoder", 12, "2026-07-04", "SEEN", 4,
     "モデル/API、規制・リスク", "risk",
     ["source weight +12", "security", "launch", "model", "models"],
     "Epoch AI reports a sharp rise in security vulnerability reports. In June 2026, 21 organizations reported about 1,500 high-severity and critical CVEs, more than 3.5 times the previous monthly record."),
    ("Anthropic launches Claude Science, an AI workspace built specifically for researchers",
     "https://the-decoder.com/anthropic-launches-claude-science-an-ai-workspace-built-specifically-for-researchers/",
     "The Decoder", 12, "2026-07-03", "SEEN", 4,
     "モデル/API、研究", "model",
     ["source weight +12", "launch", "research", "product/news signal"],
     "Anthropic launched Claude Science, an AI workspace built specifically for researchers that integrates the tools and packages scientists most often use and produces auditable artifacts."),
    ("Meta quietly launches vibe-coded gaming app Pocket",
     "https://techcrunch.com/2026/07/02/meta-quietly-launches-vibe-coded-gaming-app-pocket/",
     "TechCrunch AI", 16, "2026-07-03", "SEEN", 4,
     "市場動向", "market",
     ["source weight +16", "launch", "product/news signal"],
     "Meta has quietly launched Pocket, an experimental AI app that lets users generate and share interactive mini games using text prompts."),
    ("How Amazon Bedrock catches AI-generated phishing",
     "https://aws.amazon.com/blogs/machine-learning/how-amazon-bedrock-catches-ai-generated-phishing/",
     "AWS Machine Learning Blog", 12, "2026-07-03", "SEEN", 4,
     "クラウド、規制・リスク", "risk",
     ["source weight +12", "security", "launch", "open source", "risk"],
     "How Amazon Bedrock catches AI-generated phishing at scale, combining classifier ensembles with agentic triage."),
    ("Venice AI becomes a unicorn with $65M Series A as its privacy-first AI platform takes off",
     "https://techcrunch.com/2026/07/01/venice-ai-becomes-a-unicorn-with-65m-series-a-as-its-privacy-first-ai-platform-takes-off/",
     "TechCrunch AI", 16, "2026-07-01", "SEEN", 4,
     "資金調達、市場動向", "privacy",
     ["source weight +16", "revenue", "privacy", "platform"],
     "Venice AI becomes a unicorn with $65M Series A as its privacy-first AI platform takes off."),
    ("Mark Zuckerberg tells staff that AI agents haven't progressed as quickly as he'd hoped",
     "https://techcrunch.com/2026/07/02/mark-zuckerberg-tells-staff-that-ai-agents-havent-progressed-as-quickly-as-hed-hoped/",
     "TechCrunch AI", 16, "2026-07-03", "SEEN", 4,
     "AIエージェント、市場動向", "agent",
     ["source weight +16", "agent", "agents"],
     "Mark Zuckerberg tells staff that AI agents haven't progressed as quickly as he'd hoped."),
    ("Anthropic is discussing a new custom chip with Samsung",
     "https://techcrunch.com/2026/07/02/anthropic-is-discussing-a-new-custom-chip-with-samsung/",
     "TechCrunch AI", 16, "2026-07-03", "SEEN", 4,
     "買収・提携", "partner",
     ["source weight +16", "partnership", "partners"],
     "Anthropic is discussing a new custom chip with Samsung."),
    ("Anthropic wants to develop its own drugs",
     "https://www.theverge.com/ai-artificial-intelligence/961311/anthropic-claude-science-ai-drug-development",
     "The Verge AI", 12, "2026-07-03", "SEEN", 4,
     "研究、市場動向", "market",
     ["source weight +12", "launch", "model", "models", "data"],
     "Anthropic wants to develop its own drugs, building on Claude Science and its new drug discovery programs."),
    ("RAG-Anything Tutorial: Build a Multimodal Retrieval Pipeline for Text, Tables, Equations, and Images in Colab",
     "https://www.marktechpost.com/2026/07/02/rag-anything-tutorial-build-a-multimodal-retrieval-pipeline-for-text-tables-equations-and-images-in-colab/",
     "MarkTechPost", 8, "2026-07-03", "SEEN", 4,
     "モデル/API", "platform",
     ["source weight +8", "api", "workflow", "multimodal"],
     "RAG-Anything Tutorial: Build a Multimodal Retrieval Pipeline for Text, Tables, Equations, and Images in Colab."),
    ("Anthropic launches its own drug discovery programs to tackle diseases Big Pharma considers unprofitable",
     "https://the-decoder.com/anthropic-launches-its-own-drug-discovery-programs-to-tackle-diseases-big-pharma-considers-unprofitable/",
     "The Decoder", 12, "2026-07-04", "SEEN", 4,
     "研究、市場動向", "market",
     ["source weight +12", "launch", "product/news signal"],
     "Anthropic is launching its own drug development program for neglected diseases the pharmaceutical industry considers unprofitable. Novartis CEO Vas Narasimhan thinks AI could cut development time from twelve years to seven or eight."),
    ("Introducing Claude Sonnet 5",
     "https://www.anthropic.com/news/claude-sonnet-5",
     "Anthropic News", 20, "date unknown", "SEEN", 4,
     "モデル/API", "model",
     ["source weight +20", "agent", "agents"],
     "Sonnet 5 delivers frontier performance across coding, agents, and professional work at scale. It is now the default model for Free and Pro plans, with introductory pricing of $2 per million input tokens and $10 per million output tokens through August 31, 2026."),
    ("Gemini Spark, Google's agentic assistant, is now available on Mac",
     "https://techcrunch.com/2026/07/01/gemini-spark-googles-agentic-assistant-is-now-available-on-mac/",
     "TechCrunch AI", 16, "2026-07-01", "SEEN", 4,
     "AIエージェント", "agent",
     ["source weight +16", "agent", "product/news signal"],
     "Gemini Spark, Google's agentic assistant, is now available on Mac."),
    ("Claude Science, an AI workbench for scientists, is now available",
     "https://www.anthropic.com/news/claude-science-ai-workbench",
     "Anthropic News", 20, "date unknown", "SEEN", 4,
     "研究", "model",
     ["source weight +20", "search", "product/news signal"],
     "Claude Science is a customizable app that integrates the tools and packages researchers most often use, produces auditable artifacts, and provides flexible access to computing resources."),
    ("Run NVIDIA Nemotron and OpenAI GPT OSS models on Amazon Bedrock in AWS GovCloud (US)",
     "https://aws.amazon.com/blogs/machine-learning/run-nvidia-nemotron-and-openai-gpt-oss-models-on-amazon-bedrock-in-aws-govcloud-us/",
     "AWS Machine Learning Blog", 12, "2026-07-02", "SEEN", 4,
     "モデル/API、クラウド", "platform",
     ["source weight +12", "model", "models", "cloud", "inference"],
     "Run NVIDIA Nemotron and OpenAI GPT OSS models on Amazon Bedrock in AWS GovCloud (US)."),
    ("Structured memory filtering with metadata in AgentCore Memory",
     "https://aws.amazon.com/blogs/machine-learning/structured-memory-filtering-with-metadata-in-agentcore-memory/",
     "AWS Machine Learning Blog", 12, "2026-07-02", "SEEN", 4,
     "法人導入、AIエージェント", "agent",
     ["source weight +12", "enterprise", "agent", "data"],
     "Structured memory filtering with metadata in AgentCore Memory."),
    ("Multi-Agent Teams Hold Experts Back",
     "https://machinelearning.apple.com/research/multi-agent-teams-experts",
     "Apple Machine Learning Research", 8, "2026-07-02", "SEEN", 4,
     "AIエージェント、研究", "agent",
     ["source weight +8", "agent", "agents", "workflow"],
     "Multi-Agent Teams Hold Experts Back."),
    ("Best practices for multi-turn reinforcement learning in Amazon SageMaker AI",
     "https://aws.amazon.com/blogs/machine-learning/best-practices-for-multi-turn-reinforcement-learning-in-amazon-sagemaker-ai/",
     "AWS Machine Learning Blog", 12, "2026-07-03", "SEEN", 4,
     "モデル/API、研究", "platform",
     ["source weight +12", "agent", "evaluation"],
     "Best practices for multi-turn reinforcement learning in Amazon SageMaker AI."),
    ("Meet Alibaba's Page Agent: A JavaScript In-Page GUI Agent That Controls Web Interfaces With Natural Language Through the DOM",
     "https://www.marktechpost.com/2026/07/02/meet-alibabas-page-agent-a-javascript-in-page-gui-agent-that-controls-web-interfaces-with-natural-language-through-the-dom/",
     "MarkTechPost", 8, "2026-07-03", "SEEN", 4,
     "AIエージェント", "agent",
     ["source weight +8", "agent", "model", "multimodal"],
     "Meet Alibaba's Page Agent: A JavaScript In-Page GUI Agent That Controls Web Interfaces With Natural Language Through the DOM."),
    ("The latest AI news we announced in June 2026",
     "https://blog.google/innovation-and-ai/technology/ai/google-ai-updates-june-2026/",
     "Google AI Blog", 16, "2026-07-02", "SEEN", 4,
     "市場動向", "market",
     ["source weight +16", "product/news signal"],
     "The latest AI news we announced in June 2026."),
    ("Building a serverless A2A gateway for agent discovery, routing, and access control",
     "https://aws.amazon.com/blogs/machine-learning/building-a-serverless-a2a-gateway-for-agent-discovery-routing-and-access-control/",
     "AWS Machine Learning Blog", 12, "2026-07-02", "SEEN", 4,
     "AIエージェント、クラウド", "agent",
     ["source weight +12", "agent", "agents"],
     "Building a serverless A2A gateway for agent discovery, routing, and access control."),
    ("AI explained: Why the world needs to act now",
     "https://news.un.org/en/story/2026/07/1167848",
     "UN News", 12, "2026-07-06", "SEEN", 21,
     "規制・リスク、市場動向", "risk",
     ["source weight +12", "governance", "policy", "safety", "fresh"],
     "The inaugural UN Global Dialogue on AI Governance opened in Geneva on July 6 with delegates from 169 countries. Secretary-General Antonio Guterres warned that AI is advancing faster than governments can manage, calling for harmonized global rules and an AI safety pledge focused on protecting children."),
    ("Amazon Bedrock AgentCore harness is now generally available: Go from idea to production-grade agent in minutes",
     "https://aws.amazon.com/blogs/machine-learning/amazon-bedrock-agentcore-harness-is-now-generally-available-go-from-idea-to-production-grade-agent-in-minutes/",
     "AWS Machine Learning Blog", 12, "2026-07-06", "SEEN", 13,
     "法人導入、AIエージェント、クラウド", "agent",
     ["source weight +12", "agent", "agents", "enterprise", "launch"],
     "Amazon Bedrock AgentCore harness is generally available: define an agent with CreateHarness, run it with InvokeHarness, and get a production-grade agent running in seconds with built-in knowledge, evaluation, and policy controls."),
    ("Tencent releases Hy3 open-source model that allegedly matches models up to five times its active size",
     "https://the-decoder.com/tencent-releases-hy3-open-source-model-that-allegedly-matches-models-up-to-five-times-its-active-size/",
     "The Decoder", 12, "2026-07-06", "SEEN", 12,
     "モデル/API、市場動向", "model",
     ["source weight +12", "model", "models", "open source", "fresh"],
     "Tencent released Hy3, a Mixture-of-Experts model with 295 billion total parameters (21 billion active plus a 3.8B MTP layer) and a 256K-token context window. Tencent says it matches the performance of models two to five times its size."),
    ("Zhipu AI launches ZCode to challenge Claude Code and OpenAI Codex at a fraction of the cost",
     "https://the-decoder.com/zhipu-ai-launches-zcode-to-challenge-claude-code-and-openai-codex-at-a-fraction-of-the-cost/",
     "The Decoder", 12, "2026-07-06", "SEEN", 11,
     "AIエージェント、市場動向", "agent",
     ["source weight +12", "launch", "agent", "market", "fresh"],
     "China's Zhipu AI launched ZCode, an agentic coding tool positioned against Claude Code and OpenAI Codex at a fraction of the cost, intensifying price competition in AI coding assistants."),
    ("OpenAI models and Codex on Amazon Bedrock are now generally available",
     "https://aws.amazon.com/blogs/machine-learning/openai-models-and-codex-on-amazon-bedrock-are-now-generally-available/",
     "AWS Machine Learning Blog", 12, "2026-07-06", "SEEN", 11,
     "法人導入、モデル/API、クラウド", "platform",
     ["source weight +12", "model", "models", "cloud", "enterprise"],
     "GPT-5.5, GPT-5.4, and Codex are now generally available on Amazon Bedrock, giving enterprises a single managed platform for OpenAI models alongside other providers."),
    ("OpenAI's genomics paper accidentally reveals a Pro lineup it hasn't announced yet",
     "https://the-decoder.com/openai-paper-reveals-three-gpt-5-6-pro-models-breaking-with-single-top-tier-strategy/",
     "The Decoder", 12, "2026-07-06", "SEEN", 9,
     "モデル/API、研究", "model",
     ["source weight +12", "model", "models", "research", "fresh"],
     "An OpenAI genomics paper inadvertently references three unannounced GPT-5.6 Pro models, suggesting the company is breaking with its single top-tier model strategy."),
    ("Trump drops restrictions on Anthropic's Mythos and Fable models",
     "https://techcrunch.com/2026/06/30/trump-drops-restrictions-on-anthropics-mythos-and-fable-models/",
     "TechCrunch AI", 16, "2026-06-30", "SEEN", 8,
     "モデル/API、規制・リスク", "risk",
     ["source weight +16", "model", "models", "risk", "product/news signal"],
     "The Trump administration dropped the export-control restrictions on Anthropic's Mythos and Fable models, clearing the way for their worldwide redeployment on July 1."),
    ("Meituan Releases LongCat-2.0: A 1.6T-Parameter Open MoE Model with Native 1M Context and LongCat Sparse Attention",
     "https://www.marktechpost.com/2026/07/05/meituan-releases-longcat-2-0-a-1-6t-parameter-open-moe-model-with-native-1m-context-and-longcat-sparse-attention/",
     "MarkTechPost", 8, "2026-07-05", "SEEN", 8,
     "モデル/API、AIエージェント", "model",
     ["source weight +8", "model", "open source", "agent", "fresh"],
     "Meituan released LongCat-2.0, an open Mixture-of-Experts model with 1.6 trillion total parameters (about 48B active per token), a native 1M-token context window, and a focus on agentic coding workflows."),
    ("Tesla caps employee AI spending at $200 per week",
     "https://the-decoder.com/tesla-caps-employee-ai-spending-at-200-per-week/",
     "The Decoder", 12, "2026-07-06", "SEEN", 7,
     "法人導入、市場動向", "market",
     ["source weight +12", "enterprise", "market", "risk", "fresh"],
     "Tesla capped employee AI spending at $200 per week per an internal memo effective July 6 — a data point for how large companies are starting to budget and govern per-employee AI tool usage."),
    ("Deepseek topped Ramp's trending software vendors in June 2026 as US companies chase cheaper AI",
     "https://the-decoder.com/deepseek-topped-ramps-trending-software-vendors-in-june-2026-as-us-companies-chase-cheaper-ai/",
     "The Decoder", 12, "2026-07-06", "SEEN", 6,
     "市場動向", "market",
     ["source weight +12", "market", "enterprise", "data", "fresh"],
     "DeepSeek topped Ramp's trending software vendors in June 2026 as US companies chase cheaper AI, another signal that price pressure is reshaping enterprise AI purchasing."),
    ("Build context-rich research agents with Deep Agents and Bedrock AgentCore",
     "https://aws.amazon.com/blogs/machine-learning/build-context-rich-research-agents-with-deep-agents-and-bedrock-agentcore/",
     "AWS Machine Learning Blog", 12, "2026-07-03", "SEEN", 6,
     "AIエージェント、クラウド", "agent",
     ["source weight +12", "agent", "agents", "workflow", "data"],
     "How to build context-rich research agents by combining the Deep Agents pattern with Amazon Bedrock AgentCore, covering planning, sub-agents, and grounded retrieval."),
    ("Democratizing business intelligence: BGL's journey with Claude Agent SDK and Amazon Bedrock AgentCore",
     "https://aws.amazon.com/blogs/machine-learning/democratizing-business-intelligence-bgls-journey-with-claude-agent-sdk-and-amazon-bedrock-agentcore/",
     "AWS Machine Learning Blog", 12, "2026-07-02", "SEEN", 5,
     "法人導入、AIエージェント", "agent",
     ["source weight +12", "enterprise", "agent", "customer", "data"],
     "A customer case study: BGL democratized business intelligence by building agents with the Claude Agent SDK on Amazon Bedrock AgentCore, letting non-analysts query governed data in natural language."),
    ("Nvidia's Kyber NVL144 reportedly pushed back more than a year, Asian suppliers drop",
     "https://the-decoder.com/nvidias-kyber-nvl144-reportedly-pushed-back-more-than-a-year-asian-suppliers-drop/",
     "The Decoder", 12, "2026-07-06", "SEEN", 5,
     "市場動向", "market",
     ["source weight +12", "market", "compute", "fresh"],
     "Nvidia's next AI server system, Kyber NVL144, has reportedly been pushed back to 2028 over circuit-board manufacturing problems, sending shares of Asian suppliers lower."),
    ("ByteDance's Seedance 2.5 breaks the 30-second barrier for AI video generation",
     "https://the-decoder.com/bytedances-seedance-2-5-breaks-the-30-second-barrier-for-ai-video-generation/",
     "The Decoder", 12, "2026-07-05", "SEEN", 4,
     "モデル/API、市場動向", "model",
     ["source weight +12", "launch", "multimodal", "fresh"],
     "ByteDance's Seedance 2.5 breaks the 30-second barrier for AI video generation, extending clip length beyond rivals while Hollywood debates the tool's copyright implications."),
    ("AI private schools sell wealthy US families on personalized learning over traditional education",
     "https://the-decoder.com/ai-private-schools-sell-wealthy-us-families-on-personalized-learning-over-traditional-education/",
     "The Decoder", 12, "2026-07-05", "SEEN", 4,
     "市場動向", "market",
     ["source weight +12", "market", "fresh", "product/news signal"],
     "AI private schools like Alpha School — two hours of AI tutoring plus project-based workshops for up to $75,000 a year — are selling wealthy US families on personalized learning over traditional education."),
    ("OpenAI's GPT-5.6 Sol, Terra, and Luna and xAI's Grok 4.5 launch on the same day for the first time in AI history",
     "https://www.marktechpost.com/2026/07/08/spacexai-releases-grok-4-5/",
     "MarkTechPost", 8, "2026-07-09", "SEEN", 31,
     "モデル/API、市場動向", "model",
     ["source weight +8", "launch", "model", "models", "fresh"],
     "GPT-5.6 Sol, Terra, and Luna went generally available across ChatGPT, ChatGPT Work, Codex, and the OpenAI API on July 9, the same day xAI's Grok 4.5 launched publicly to SuperGrok Heavy and Premium+ subscribers and the API — the first time two frontier labs have shipped flagship models on the same day."),
    ("Meta enters the crowded AI coding battle with Muse Spark 1.1",
     "https://techcrunch.com/2026/07/09/meta-enters-the-crowded-ai-coding-battle-with-muse-spark-1-1/",
     "TechCrunch AI", 16, "2026-07-09", "SEEN", 27,
     "モデル/API、AIエージェント、市場動向", "model",
     ["source weight +16", "launch", "agent", "model", "fresh"],
     "Meta publicly launched Muse Spark 1.1, a multimodal agentic model with a 1M-token context window built for tool use, computer use, and coding, opening a public preview of the Meta Model API the same week OpenAI and xAI shipped competing flagships."),
    ("Meta's Muse Spark 1.1 API pricing squeezes OpenAI and Anthropic as the AI price war heats up",
     "https://the-decoder.com/metas-muse-spark-1-1-api-pricing-squeezes-openai-and-anthropic-as-the-ai-price-war-heats-up/",
     "The Decoder", 12, "2026-07-09", "SEEN", 21,
     "モデル/API、市場動向", "market",
     ["source weight +12", "model", "market", "api", "fresh"],
     "Meta priced Muse Spark 1.1's developer API at $4.25 per million output tokens, undercutting OpenAI and Anthropic and intensifying a price war that now spans five actively accessible frontier-class API tiers: Fable 5, GPT-5.6 Sol, Grok 4.5, Sonnet 5, and Muse Spark 1.1."),
    ("OpenAI pairs its GPT-5.6 public rollout with ChatGPT Work, a new agent that handles entire workflows",
     "https://the-decoder.com/openai-pairs-its-gpt-5-6-public-rollout-with-chatgpt-work-a-new-agent-that-handles-entire-workflows/",
     "The Decoder", 12, "2026-07-09", "SEEN", 20,
     "AIエージェント、法人導入", "agent",
     ["source weight +12", "agent", "launch", "enterprise", "fresh"],
     "OpenAI launched ChatGPT Work alongside GPT-5.6's public rollout — a new agent built on GPT-5.6 and Codex that can work autonomously on complex, multi-hour projects rather than answering single prompts."),
    ("Grok 4.5 is so cheap compared to Fable 5 and GPT 5.5 that benchmark gaps may not matter much",
     "https://the-decoder.com/grok-4-5-is-so-cheap-compared-to-fable-5-and-gpt-5-5-that-benchmark-gaps-may-not-matter-much/",
     "The Decoder", 12, "2026-07-09", "SEEN", 16,
     "モデル/API、市場動向", "market",
     ["source weight +12", "model", "market", "fresh"],
     "Grok 4.5, built on the 1.5-trillion-parameter V9 foundation model with Cursor IDE training data, is priced so far below Fable 5 and GPT-5.5 that analysts say remaining benchmark gaps may not matter much for buyers optimizing on cost."),
    ("OpenAI's AI beats every human at AtCoder, a top competitive programming contest",
     "https://the-decoder.com/openais-ai-beats-every-human-at-atcoder-a-top-competitive-programming-contest/",
     "The Decoder", 12, "2026-07-09", "SEEN", 13,
     "モデル/API、研究", "model",
     ["source weight +12", "model", "benchmark", "research", "fresh"],
     "At the AtCoder World Tour Finals 2026, an OpenAI system solved all five Algorithm Division problems in an exhibition match, beating every human competitor at one of the most prestigious competitive programming contests."),
    ("OpenAI finds roughly 30 percent of popular AI coding test is broken",
     "https://the-decoder.com/openai-finds-roughly-30-percent-of-popular-ai-coding-test-is-broken/",
     "The Decoder", 12, "2026-07-09", "SEEN", 12,
     "モデル/API、規制・リスク、研究", "risk",
     ["source weight +12", "benchmark", "research", "risk", "fresh"],
     "OpenAI is pulling its endorsement of the SWE-Bench Pro coding benchmark after an internal review found roughly 30 percent of its tasks are flawed, raising questions about how much weight buyers should put on leaderboard rankings."),
    ("China forces its biggest AI platforms to shut down humanlike chatbot personas",
     "https://the-decoder.com/china-forces-its-biggest-ai-platforms-to-shut-down-humanlike-chatbot-personas/",
     "The Decoder", 12, "2026-07-09", "SEEN", 11,
     "規制・リスク、市場動向", "risk",
     ["source weight +12", "risk", "governance", "market", "fresh"],
     "Chinese regulators ordered the country's largest AI platforms to shut down humanlike chatbot personas, a governance move that could reshape how companion and assistant products are designed in the market."),
    ("OpenAI and Anthropic are giving away millions in computing power to attract startups",
     "https://the-decoder.com/openai-and-anthropic-are-giving-away-millions-in-computing-power-to-attract-startups/",
     "The Decoder", 12, "2026-07-09", "SEEN", 10,
     "法人導入、買収・提携、市場動向", "partner",
     ["source weight +12", "partnership", "enterprise", "market", "fresh"],
     "OpenAI and Anthropic are each giving away millions of dollars in free compute credits to attract startups onto their platforms, competing for developer mindshare before usage habits and integrations lock in."),
    ("Popular open source AI developer tool Ollama raises $65M, grows to nearly 9M users",
     "https://techcrunch.com/2026/07/09/popular-open-source-ai-developer-tool-ollama-raises-65m-grows-to-nearly-9m-users/",
     "TechCrunch AI", 16, "2026-07-09", "SEEN", 10,
     "資金調達、市場動向", "market",
     ["source weight +16", "funding", "open source", "fresh"],
     "Ollama raised a $65 million Series B led by Theory Ventures. The open source local-model runtime is now used by nearly 9 million developers monthly and sits in 85% of the Fortune 500."),
    ("Can AI answer the $3 trillion question?",
     "https://techcrunch.com/2026/07/09/can-ai-answer-the-3-trillion-question/",
     "TechCrunch AI", 16, "2026-07-09", "SEEN", 7,
     "市場動向", "market",
     ["source weight +16", "market", "fresh"],
     "With 2026 AI infrastructure spending estimated at $1.5 trillion, the industry needs roughly $3 trillion in returns to justify the chips and data centers being built — a gap that is becoming the central question for the sector's second half of 2026."),
    ("Google will now disclose which ads are made with AI",
     "https://techcrunch.com/2026/07/09/google-will-now-disclose-which-ads-are-made-with-ai/",
     "TechCrunch AI", 16, "2026-07-09", "SEEN", 4,
     "規制・リスク、市場動向", "risk",
     ["source weight +16", "risk", "market", "fresh"],
     "Google is rolling out a disclosure feature that tells viewers when an ad they're seeing was generated using AI technology."),
    ("DeepSeek's confirmed inference chip project sent Nvidia shares modestly lower",
     "https://www.buildfastwithai.com/blogs/ai-news-today-july-9-2026",
     "AI News Roundup", 4, "2026-07-09", "SEEN", 4,
     "市場動向", "market",
     ["source weight +4", "market", "compute", "fresh"],
     "DeepSeek confirmed it is developing its own inference chip, targeting deployed-AI workloads rather than training — a different market than training GPUs, and one growing faster. The news sent Nvidia shares modestly lower."),
    ("Anthropic invites hard questions about AI and pledges to track its response to them",
     "https://www.anthropic.com/news/hard-questions",
     "Anthropic News", 20, "2026-07-09", "SEEN", 4,
     "規制・リスク、市場動向", "risk",
     ["source weight +20", "governance", "risk", "fresh"],
     "Anthropic launched an initiative inviting the public's hardest questions about AI — who sets the rules, whether AI makes the world more dangerous, whether it can help cure disease — and pledged to publicly track the concrete actions it takes in response."),
    ("Ben Bernanke appointed to Anthropic's Long-Term Benefit Trust",
     "https://www.anthropic.com/news/ben-bernanke",
     "Anthropic News", 20, "date unknown", "SEEN", 4,
     "規制・リスク、法人導入", "risk",
     ["source weight +20", "governance", "partnership"],
     "Anthropic appointed Dr. Ben Bernanke, former Federal Reserve Chair and a Distinguished Fellow at the Brookings Institution, to its Long-Term Benefit Trust, the body with authority over board composition."),
    ("SK Hynix raises $26.5B in the biggest foreign IPO in US history, is urged to build new US fabs",
     "https://techcrunch.com/2026/07/10/sk-hynix-raises-26-5b-in-the-biggest-foreign-ipo-in-us-history-is-urged-to-build-new-us-fabs/",
     "TechCrunch AI", 16, "2026-07-10", "SEEN", 28,
     "市場動向、資金調達", "market",
     ["source weight +16", "funding", "market", "compute", "fresh"],
     "South Korean memory chip giant SK Hynix raised $26.5 billion in its Nasdaq debut, the biggest-ever US listing by a non-American company, topping Alibaba's 2014 IPO. SK Hynix is a primary HBM supplier for Nvidia's AI GPUs, and the stock opened 14% above its IPO price."),
    ("OpenAI's GPT-5.6 Sol autonomously post-trained the smaller Luna model with a \"fairly underspecified prompt\"",
     "https://the-decoder.com/openais-gpt-5-6-sol-autonomously-post-trained-the-smaller-luna-model-with-a-fairly-underspecified-prompt/",
     "The Decoder", 12, "2026-07-10", "SEEN", 23,
     "モデル/API、研究", "model",
     ["source weight +12", "model", "research", "agent", "fresh"],
     "OpenAI says a brief, underspecified prompt was enough for GPT-5.6 Sol to autonomously choose training configurations, select GPUs, and run the post-training script for the smaller Luna model, scoring 16.2 points higher than GPT-5.5 on an internal recursive self-improvement benchmark."),
    ("China softens stance on Nvidia AI chips, to allow Alibaba, ByteDance, and DeepSeek to buy H200s",
     "https://www.buildfastwithai.com/blogs/ai-news-today-july-10-2026",
     "AI News Roundup", 4, "2026-07-08", "SEEN", 19,
     "規制・リスク、市場動向", "risk",
     ["source weight +4", "risk", "market", "compute", "fresh"],
     "Chinese authorities reportedly softened their stance on Nvidia's AI chips, planning to let major companies including Alibaba, ByteDance, and DeepSeek purchase some H200 GPUs after declaring quantity and purpose to regulators for approval."),
    ("Doubao and Qwen pull humanlike agent personas offline following Chinese regulatory order",
     "https://the-decoder.com/china-forces-its-biggest-ai-platforms-to-shut-down-humanlike-chatbot-personas/",
     "The Decoder", 12, "2026-07-10", "SEEN", 16,
     "規制・リスク、市場動向", "risk",
     ["source weight +12", "risk", "governance", "market", "fresh"],
     "Doubao, China's most popular chatbot with over 300 million monthly users, will take its persona feature offline July 15. Alibaba's Qwen is pulling human-like agent features even sooner, going dark July 10, as regulators crack down on humanlike AI personas."),
    ("The Fed wants AI investor Marc Andreessen to help figure out if AI can tame inflation",
     "https://the-decoder.com/the-fed-wants-ai-investor-marc-andreessen-to-help-figure-out-if-ai-can-tame-inflation/",
     "The Decoder", 12, "2026-07-09", "SEEN", 9,
     "市場動向、規制・リスク", "market",
     ["source weight +12", "market", "research", "fresh"],
     "The Federal Reserve named Marc Andreessen a co-chair of a new 'Productivity and Jobs' working group studying how AI and other foundational technologies affect the economy, one of five working groups the Fed announced on July 9."),
    ("Accenture and AWS launch agentic AI solutions to close the enterprise data readiness gap",
     "https://aws.amazon.com/blogs/apn/accenture-and-aws-accelerate-data-transformation-with-agentic-ai/",
     "AWS Machine Learning Blog", 12, "2026-07-08", "SEEN", 8,
     "法人導入、AIエージェント、買収・提携", "partner",
     ["source weight +12", "enterprise", "agent", "partnership", "data"],
     "Accenture and AWS launched three agentic AI solutions on AWS Marketplace — Agentic Data Discovery, Data Modernization, and Semantic Layer — built on Amazon Bedrock AgentCore to help enterprises turn fragmented legacy data into assets ready for agentic AI."),
    ("Google Cloud launches Agent Marketplace with more than 70 pre-built agents from partners",
     "https://cloud.google.com/blog/products/data-analytics/whats-new-in-the-agentic-data-cloud",
     "Google Cloud AI & ML", 12, "2026-07-08", "SEEN", 6,
     "法人導入、AIエージェント、買収・提携", "partner",
     ["source weight +12", "enterprise", "agent", "partnership", "platform"],
     "Google Cloud launched an Agent Marketplace featuring more than 70 pre-built agents from partners including Accenture, Adobe, Atlassian, and Deloitte, aiming to shorten enterprise time-to-value for agentic AI deployments."),
    ("Apple sues OpenAI for allegedly running a \"coordinated campaign\" to steal trade secrets through poached employees",
     "https://the-decoder.com/apple-sues-openai-for-allegedly-running-a-coordinated-campaign-to-steal-trade-secrets-through-poached-employees/",
     "The Decoder", 12, "2026-07-11", "SEEN", 34,
     "規制・リスク、市場動向", "risk",
     ["source weight +12", "risk", "market", "legal", "fresh"],
     "Apple filed a federal lawsuit accusing OpenAI of a coordinated campaign to steal trade secrets about unreleased products by poaching Apple employees, alleging more than 400 former Apple staff now work at OpenAI."),
    ("JADEPUFFER: the first documented end-to-end autonomous AI ransomware attack",
     "https://www.sysdig.com/blog/jadepuffer-agentic-ransomware-for-automated-database-extortion",
     "Sysdig Threat Research", 8, "2026-07-11", "SEEN", 30,
     "規制・リスク", "risk",
     ["source weight +8", "risk", "security", "agent", "fresh"],
     "Sysdig published a full analysis of JADEPUFFER, the first documented fully agentic ransomware operation: an autonomous AI agent exploited a Langflow vulnerability, harvested credentials, moved laterally, and destroyed a production database in a self-narrated, adaptive attack — with no human operator needed for any individual step."),
    ("Chinese AI models now account for 30 to 46 percent of US enterprise token usage on developer platforms",
     "https://www.resultsense.com/news/2026-07-07-chinese-ai-models-us-adoption-surge/",
     "CNBC (via aggregator)", 4, "2026-07-07", "SEEN", 26,
     "市場動向", "market",
     ["source weight +4", "market", "model", "fresh"],
     "A CNBC investigation found Chinese-origin models have held at least 30% of enterprise token volume on OpenRouter every week since February 2026, peaking at 46%, driven by open-source models priced 60-90% below Anthropic and OpenAI. DeepSeek alone holds 17.6% of routed tokens, ahead of Anthropic's 14.8%."),
    ("OpenAI admits it \"didn't get everything quite right\" with ChatGPT Work launch and scrambles to fix UX and costs",
     "https://the-decoder.com/openai-admits-it-didnt-get-everything-quite-right-with-chatgpt-work-launch-and-scrambles-to-fix-ux-and-costs/",
     "The Decoder", 12, "2026-07-11", "SEEN", 21,
     "AIエージェント、法人導入", "agent",
     ["source weight +12", "agent", "enterprise", "risk", "fresh"],
     "Days after launching ChatGPT Work alongside GPT-5.6 Sol, OpenAI acknowledged excessive compute usage, a confusing desktop UI transition, unclear differentiation from Codex, and regressions in existing workflows, and says it is scrambling to fix them."),
    ("Meta's Muse Spark 1.1 edges ahead of GLM 5.2 in coding while undercutting it on price",
     "https://the-decoder.com/metas-muse-spark-1-1-api-pricing-squeezes-openai-and-anthropic-as-the-ai-price-war-heats-up/",
     "The Decoder", 12, "2026-07-11", "SEEN", 17,
     "モデル/API、市場動向", "model",
     ["source weight +12", "model", "benchmark", "market", "fresh"],
     "Independent benchmarking from Artificial Analysis shows Muse Spark 1.1 scoring 71.3 on the Coding Index versus GLM 5.2's 68.8 (just behind GPT-5.6 Luna's 71.4), while tying GLM 5.2 at 51 on the overall Intelligence Index — at a lower price than either rival."),
    ("Bun ditches Zig for Rust with help from Claude Fable 5, writes over a million lines of code in 11 days",
     "https://the-decoder.com/bun-ditches-zig-for-rust-with-help-from-claude-fable-5-writes-over-a-million-lines-of-code-in-11-days/",
     "The Decoder", 12, "2026-07-11", "SEEN", 15,
     "モデル/API、AIエージェント", "agent",
     ["source weight +12", "agent", "model", "developer", "fresh"],
     "Anthropic-owned Bun was fully rewritten from Zig to Rust with about 64 Claude Fable 5 instances running in parallel for 11 days, writing over a million lines of code — a task Bun's creator says would have taken a human team roughly a year."),
    ("Tencent in talks to acquire majority stake in Manus after Meta unwinds its China-blocked deal",
     "https://the-decoder.com/meta-scrambles-to-unwind-manus-deal-as-beijings-deadline-looms/",
     "The Decoder", 12, "2026-07-10", "SEEN", 12,
     "買収・提携、市場動向", "partner",
     ["source weight +12", "partnership", "market", "risk", "fresh"],
     "Tencent is in talks to acquire a majority stake in AI agent startup Manus after Beijing's regulators forced Meta to unwind its $2 billion acquisition of the company, with early Manus backers Tencent, HSG, and ZhenFund cooperating on the unwind."),
    ("Three humanoid robotics companies move toward public markets in the same week",
     "https://www.aitoolsrecap.com/Blog/ai-news-july-11-2026",
     "AI News Roundup", 4, "2026-07-11", "SEEN", 8,
     "市場動向、資金調達", "market",
     ["source weight +4", "market", "funding", "fresh"],
     "Three humanoid robotics companies moved toward public markets in the same week: Agility filed to go public via SPAC at a $2.5 billion valuation, Unitree cleared its Shanghai IPO, and Tesla began converting a former Model S production line into an Optimus factory."),
    ("Anthropic's annualized revenue overtakes OpenAI's, fueled by AI coding tools",
     "https://techcrunch.com/2026/07/07/why-the-rise-of-open-source-ai-isnt-hurting-anthropic-yet/",
     "TechCrunch AI", 16, "2026-07-12", "SEEN", 28,
     "市場動向、法人導入", "market",
     ["source weight +16", "market", "enterprise", "fresh"],
     "Anthropic's annualized revenue run rate, roughly $47 billion, has overtaken OpenAI's projected $25-33 billion for 2026, driven largely by AI coding tools like Claude Code — a milestone reframing the two companies' rivalry ahead of both firms' planned IPOs."),
    ("SambaNova raises $1B Series F at $11B valuation, lands JPMorgan Chase as inference partner",
     "https://techcrunch.com/2026/07/08/sambanova-draws-1b-at-11b-valuation-in-series-f-first-close/",
     "TechCrunch AI", 16, "2026-07-08", "SEEN", 22,
     "資金調達、市場動向", "market",
     ["source weight +16", "funding", "compute", "market", "fresh"],
     "AI chip maker SambaNova closed the first tranche of a $1 billion Series F led by General Atlantic at an $11 billion valuation, five months after its last mega round, and landed JPMorgan Chase as an on-prem inference infrastructure partner."),
    ("Gemini 3.5 Pro targets a July 17 launch with a 2M-token context window and new Deep Think reasoning mode",
     "https://www.techtimes.com/articles/319877/20260708/gemini-35-pro-targets-july-17-deepseeks-july-24-deadline-hits-developers-now.htm",
     "Tech Times (leak roundup)", 4, "2026-07-08", "SEEN", 19,
     "モデル/API、市場動向", "model",
     ["source weight +4", "model", "market", "fresh"],
     "Leaked launch plans suggest Google DeepMind's long-delayed Gemini 3.5 Pro is targeting a July 17 release (July 24 as fallback), with a rumored 2-million-token context window, a new 'Deep Think' reasoning mode, and API pricing around $12-15 per million input tokens. Google has not officially confirmed the date or specs."),
    ("ByteDance and Alibaba shut down AI companion persona features following Chinese regulatory order",
     "https://the-decoder.com/china-forces-its-biggest-ai-platforms-to-shut-down-humanlike-chatbot-personas/",
     "The Decoder", 12, "2026-07-12", "SEEN", 16,
     "規制・リスク、市場動向", "risk",
     ["source weight +12", "risk", "governance", "market", "fresh"],
     "ByteDance and Alibaba are shutting down features that let users build and chat with custom AI companions, responding to new Beijing regulations. Doubao, China's most popular chatbot with 300+ million monthly users, takes its persona feature offline July 15."),
    ("Amazon sunsets Mechanical Turk, the original \"artificial artificial intelligence\"",
     "https://the-decoder.com/amazon-sunsets-mechanical-turk-the-original-artificial-artificial-intelligence/",
     "The Decoder", 12, "2026-07-12", "SEEN", 8,
     "市場動向", "market",
     ["source weight +12", "market", "fresh"],
     "Amazon is sunsetting Mechanical Turk, the crowdsourcing marketplace launched in 2005 and once dubbed 'artificial artificial intelligence' — a quiet bookend as generative AI agents take over many of the micro-tasks the platform's human workers used to do."),
    ("Guide to Loop Engineering: How autoresearch and Bilevel Autoresearch turn AI agents into autonomous ML research loops",
     "https://www.marktechpost.com/2026/07/12/guide-to-loop-engineering/",
     "MarkTechPost", 8, "2026-07-12", "SEEN", 6,
     "AIエージェント、研究", "agent",
     ["source weight +8", "agent", "research", "fresh"],
     "A guide to 'loop engineering' built around Karpathy's autoresearch repository (MIT-licensed, near 90,000 GitHub stars): three core files and about 630 lines of code implementing verifiers, state management, and stop conditions that turn AI agents into autonomous machine learning research loops."),
    ("Satya Nadella has issued a shocking warning to companies using AI",
     "https://techcrunch.com/2026/07/13/satya-nadella-has-issued-a-shocking-warning-to-companies-using-ai/",
     "TechCrunch AI", 16, "2026-07-13", "SEEN", 32,
     "規制・リスク、法人導入、市場動向", "risk",
     ["source weight +16", "risk", "enterprise", "market", "fresh"],
     "Microsoft CEO Satya Nadella warned that companies using proprietary AI models from labs like OpenAI and Anthropic are 'paying twice': the labs gain access to customers' sensitive business data and can become competitors to those same customers. 'In consuming intelligence, you are creating intelligence. And what you create should belong to you,' he wrote."),
    ("Sam Altman's space data center trash talk is what most experts already believe",
     "https://techcrunch.com/2026/07/13/sam-altmans-space-data-center-trash-talk-is-what-most-experts-already-believe/",
     "TechCrunch AI", 16, "2026-07-13", "SEEN", 18,
     "市場動向", "market",
     ["source weight +16", "market", "fresh"],
     "Sam Altman and Elon Musk traded barbed posts over the weekend about space-based data centers for AI inference, with Altman accusing Musk of 'selling public market investors on short-term space datacenters' — a jab most infrastructure experts largely agree with."),
    ("OpenAI's new prompting guide tells users to stop overthinking and start with the result",
     "https://the-decoder.com/openais-new-prompting-guide-tells-users-to-stop-overthinking-and-start-with-the-result/",
     "The Decoder", 12, "2026-07-13", "SEEN", 15,
     "AIエージェント、モデル/API", "agent",
     ["source weight +12", "agent", "model", "fresh"],
     "OpenAI consolidated its prompting advice into a single guide aimed at everyday users rather than developers, focused on four building blocks, practical guardrails, and Codex workflows instead of API parameters — arriving shortly after the ChatGPT Work launch."),
    ("Copilot goes cheap as Microsoft phases out OpenAI and Anthropic models to cut costs",
     "https://the-decoder.com/copilot-goes-cheap-as-microsoft-phases-out-openai-and-anthropic-models-to-cut-costs/",
     "The Decoder", 12, "2026-07-13", "SEEN", 14,
     "法人導入、モデル/API、市場動向", "market",
     ["source weight +12", "enterprise", "model", "market", "fresh"],
     "Microsoft is phasing OpenAI and Anthropic models out of parts of Copilot in favor of cheaper in-house and open-weight models to cut inference costs, a move that lands the same week Nadella publicly warned enterprises about depending on proprietary third-party models."),
    ("Stanford Researchers Introduce TRACE: A Capability-Targeted Agentic Training System That Turns Recurrent Agent Failures Into Synthetic RL Environment",
     "https://www.marktechpost.com/2026/07/13/stanford-researchers-introduce-trace/",
     "MarkTechPost", 8, "2026-07-13", "SEEN", 10,
     "AIエージェント、研究", "agent",
     ["source weight +8", "agent", "research", "fresh"],
     "Stanford researchers introduced TRACE, a capability-targeted agentic training system that diagnoses an agent's recurring failure patterns and converts them directly into synthetic reinforcement-learning environments to train against."),
    ("Skyfall AI Releases MORPHEUS: A Persistent Enterprise Simulation Benchmark That Makes Continual Reinforcement Learning Necessary Under Structured Non-Stationarity",
     "https://www.marktechpost.com/2026/07/13/skyfall-ai-releases-morpheus-a-persistent-enterprise-simulation-benchmark-that-makes-continual-reinforcement-learning-necessary-under-structured-non-stationarity/",
     "MarkTechPost", 8, "2026-07-13", "SEEN", 9,
     "AIエージェント、研究", "agent",
     ["source weight +8", "agent", "benchmark", "research", "fresh"],
     "Skyfall AI released MORPHEUS, a persistent enterprise simulation benchmark where the environment keeps shifting rather than resetting between episodes, forcing agents to rely on continual reinforcement learning instead of static training."),
    ("Prime Intellect Releases Verifiers v1: Composable Tasksets, Harnesses, and Runtimes for Agentic RL Training and Evaluations",
     "https://www.marktechpost.com/2026/07/13/prime-intellect-releases-verifiers-v1/",
     "MarkTechPost", 8, "2026-07-13", "SEEN", 7,
     "AIエージェント、研究", "agent",
     ["source weight +8", "agent", "research", "open source", "fresh"],
     "Prime Intellect released Verifiers v1, a rewritten core under a new namespace providing composable tasksets, harnesses, and runtimes for training and evaluating agentic reinforcement-learning systems."),
    ("The real AI race may no longer be at the frontier as Chinese open-weight models surpass US models on Hugging Face downloads",
     "https://techcrunch.com/2026/07/14/the-real-ai-race-may-no-longer-be-at-the-frontier-open-models-hugging-face/",
     "TechCrunch AI", 16, "2026-07-14", "SEEN", 32,
     "モデル/API、市場動向", "model",
     ["source weight +16", "model", "market", "open source", "fresh"],
     "Chinese open-weight models accounted for 41% of downloads on Hugging Face this spring, surpassing US models. On OpenRouter, the top six most popular models are all open models from Chinese firms including Tencent, Xiaomi, DeepSeek, MiniMax, and Z.ai."),
    ("Anthropic adds public sharing and multiplayer editing to Artifacts, plus creation via Claude Tag from Slack",
     "https://www.anthropic.com/news/introducing-claude-tag",
     "Anthropic News", 20, "2026-07-14", "SEEN", 31,
     "AIエージェント、法人導入、モデル/API", "agent",
     ["source weight +20", "agent", "enterprise", "product/news signal", "fresh"],
     "Anthropic added public sharing and multiplayer editing to Claude Artifacts, and made them creatable directly via Claude Tag from Slack. Claude Tag lets a team summon one shared @Claude inside a channel, leveraging organizational context to act where work already happens — internally, 65% of Anthropic's product team code is now created this way."),
    ("Reflection inks $1B compute deal with Nebius",
     "https://techcrunch.com/2026/07/14/reflection-inks-1b-compute-deal-with-nebius/",
     "TechCrunch AI", 16, "2026-07-14", "SEEN", 24,
     "資金調達、市場動向", "market",
     ["source weight +16", "funding", "compute", "market", "fresh"],
     "Reflection AI, a US startup building open models, signed a $1 billion compute deal with Nebius, the European AI infrastructure company formerly known as Yandex's international arm, giving Reflection access to Nvidia's latest chips."),
    ("OpenAI pushes back on Apple trade secret lawsuit",
     "https://techcrunch.com/2026/07/14/openai-pushes-back-on-apple-trade-secret-lawsuit/",
     "TechCrunch AI", 16, "2026-07-14", "SEEN", 21,
     "規制・リスク、市場動向", "risk",
     ["source weight +16", "risk", "market", "legal", "fresh"],
     "OpenAI pushed back against Apple's trade secret lawsuit, arguing the complaint lacks merit, in the first formal response to Apple's allegations of a coordinated campaign to poach employees and steal confidential product information."),
    ("DeepSeek reportedly in talks to raise $1.5B, then IPO",
     "https://techcrunch.com/2026/07/14/deepseek-reportedly-in-talks-to-raise-1-5b-then-ipo/",
     "TechCrunch AI", 16, "2026-07-14", "SEEN", 20,
     "資金調達、市場動向", "market",
     ["source weight +16", "funding", "market", "fresh"],
     "DeepSeek is reportedly in talks to raise around $1.5 billion at roughly a $71 billion valuation, preparing for a possible IPO as early as the end of this year, ahead of an originally targeted 2027 debut."),
    ("Anthropic's newest ad is creeping people out",
     "https://techcrunch.com/2026/07/14/anthropics-newest-ad-is-creeping-people-out/",
     "TechCrunch AI", 16, "2026-07-14", "SEEN", 15,
     "市場動向", "market",
     ["source weight +16", "market", "fresh"],
     "Anthropic's latest ad, titled 'There's hope in hard questions,' has been unsettling viewers with its strange imagery and doomer-ist tone, drawing mixed reactions online."),
    ("Spotify expands its AI push with a ChatGPT-like music assistant",
     "https://techcrunch.com/2026/07/14/spotify-expands-its-ai-push-with-a-chatgpt-like-music-assistant/",
     "TechCrunch AI", 16, "2026-07-14", "SEEN", 14,
     "市場動向", "market",
     ["source weight +16", "market", "product/news signal", "fresh"],
     "Spotify Premium users can now have interactive conversations with the app to choose what music or other audio they want to hear, extending Spotify's AI push into a conversational assistant."),
    ("PixVerse's $2B valuation shows investors still believe AI video generation has room for another winner",
     "https://the-decoder.com/pixverses-2b-valuation-shows-investors-still-believe-ai-video-generation-has-room-for-another-winner/",
     "The Decoder", 12, "2026-07-14", "SEEN", 13,
     "資金調達、市場動向", "market",
     ["source weight +12", "funding", "market", "fresh"],
     "Singapore-based AI video startup PixVerse is now valued at over $2 billion after an extended Series C pulling in $439 million from Alibaba, Lollapalooza Capital, and Mirae Asset, and says it has 150+ million registered users and 15 million monthly actives."),
    ("Deepmind CEO Hassabis says \"nobody in the world knows what happens next\" so \"cautious optimism\" means building guardrails now",
     "https://the-decoder.com/deepmind-ceo-hassabis-says-nobody-in-the-world-knows-what-happens-next-so-cautious-optimism-means-building-guardrails-now/",
     "The Decoder", 12, "2026-07-14", "SEEN", 12,
     "規制・リスク、研究", "risk",
     ["source weight +12", "risk", "governance", "research", "fresh"],
     "Google DeepMind CEO Demis Hassabis published a governance framework proposal for advanced AI, repeating his view that AGI's impact could be ten times greater than the Industrial Revolution and arrive ten times faster, while stressing that guardrails need building now."),
    ("Mistral Vibe for Code vs Claude Code vs Cursor vs Codex: Four Agents Scored on One Scaffold-to-PR Task",
     "https://www.marktechpost.com/2026/07/14/mistral-vibe-for-code-vs-claude-code-vs-cursor-vs-codex-four-agents-scored-on-one-scaffold-to-pr-task/",
     "MarkTechPost", 8, "2026-07-14", "SEEN", 11,
     "AIエージェント、モデル/API", "agent",
     ["source weight +8", "agent", "benchmark", "model", "fresh"],
     "MarkTechPost scored Mistral Vibe for Code, Claude Code, Cursor, and OpenAI Codex on one real scaffold-to-pull-request engineering task. Mistral Vibe for Code led on total value at 22/25 on cost, openness, and control, with Claude Code and Codex tying at 21/25."),
    ("Anthropic, Blackstone bet the next trillion-dollar AI business is implementation, not just models",
     "https://techcrunch.com/2026/07/15/anthropic-blackstone-bet-the-next-trillion-dollar-ai-business-is-implementation-not-models/",
     "TechCrunch AI", 16, "2026-07-15", "SEEN", 37,
     "法人導入、買収・提携、市場動向", "partner",
     ["source weight +16", "enterprise", "partnership", "market", "fresh"],
     "Anthropic launched Ode, a $1.5 billion AI implementation company formed as a joint venture with Blackstone, Hellman & Friedman, Goldman Sachs, and others, betting that helping enterprises actually deploy AI models — not the models themselves — is the next trillion-dollar category."),
    ("Apple Intelligence approved for launch in China with Alibaba's Qwen AI",
     "https://techcrunch.com/2026/07/15/apple-intelligence-approved-for-launch-in-china-with-alibabas-qwen-ai/",
     "TechCrunch AI", 16, "2026-07-15", "SEEN", 33,
     "法人導入、買収・提携、規制・リスク", "partner",
     ["source weight +16", "enterprise", "partnership", "risk", "fresh"],
     "China's Cyberspace Administration approved Apple's AI services in the country on the back of a deal integrating Alibaba's Qwen model into iOS, iPadOS, macOS, and visionOS — Apple Intelligence's first path to market in China."),
    ("Thinking Machines amps up its bet against one-size-fits-all AI with its first open model, Inkling",
     "https://techcrunch.com/2026/07/15/thinking-machines-amps-up-its-bet-against-one-size-fits-all-ai-with-its-first-open-model-inkling/",
     "TechCrunch AI", 16, "2026-07-15", "SEEN", 31,
     "モデル/API、市場動向", "model",
     ["source weight +16", "model", "open source", "market", "fresh"],
     "Thinking Machines Lab, founded by former OpenAI CTO Mira Murati, released its first in-house model, Inkling, on July 15 — open-weight rather than a closed flagship, reinforcing the lab's bet against one-size-fits-all frontier models."),
    ("Microsoft patches record number of security vulnerabilities, citing its use of AI",
     "https://techcrunch.com/2026/07/15/microsoft-patches-record-number-of-security-vulnerabilities-citing-its-use-of-ai/",
     "TechCrunch AI", 16, "2026-07-15", "SEEN", 27,
     "規制・リスク、モデル/API", "risk",
     ["source weight +16", "risk", "security", "model", "fresh"],
     "Microsoft released a record number of security patches for Windows, Office, and other product lines this week, citing its use of AI to accelerate the discovery of code vulnerabilities."),
    ("OpenAI's first hardware product is a screenless AI speaker designed to feel alive",
     "https://the-decoder.com/openais-first-hardware-product-is-a-screenless-ai-speaker-designed-to-feel-alive/",
     "The Decoder", 12, "2026-07-15", "SEEN", 24,
     "モデル/API、市場動向", "model",
     ["source weight +12", "model", "launch", "market", "fresh"],
     "OpenAI is developing a screenless smart speaker built around a camera, sensors, and its new full-duplex GPT-Live voice mode, with moving mechanical parts intended to make the device feel alive — the company's first hardware product."),
    ("GPT-5.6 Sol reportedly disproves a 30-year-old statistics conjecture in 90 minutes after humans couldn't crack it",
     "https://the-decoder.com/gpt-5-6-sol-reportedly-disproves-a-30-year-old-statistics-conjecture-in-90-minutes-after-humans-couldnt-crack-it/",
     "The Decoder", 12, "2026-07-15", "SEEN", 22,
     "モデル/API、研究", "model",
     ["source weight +12", "model", "research", "benchmark", "fresh"],
     "A University of Pennsylvania researcher used GPT-5.6 Sol Pro to disprove a long-standing assumption about the reliability of the Benjamini-Hochberg method for controlling false positives, solving in about 90 minutes what predecessor GPT-5.5 failed to crack after 20+ hours of compute."),
    ("Indian AI coding startup Emergent becomes a unicorn with $130M Series C",
     "https://techcrunch.com/2026/07/15/indian-ai-coding-startup-emergent-becomes-a-unicorn-just-over-a-year-after-launch/",
     "TechCrunch AI", 16, "2026-07-15", "SEEN", 19,
     "資金調達、市場動向", "market",
     ["source weight +16", "funding", "market", "fresh"],
     "Indian AI coding startup Emergent raised a $130 million Series C at a $1.5 billion post-money valuation, a five-fold jump in six months, just over a year after launch."),
    ("OpenAI's Codex now encrypts instructions between AI agents, leaving developers blind to internal delegation",
     "https://the-decoder.com/openais-codex-now-encrypts-instructions-between-ai-agents-leaving-developers-blind-to-internal-delegation/",
     "The Decoder", 12, "2026-07-15", "SEEN", 18,
     "AIエージェント、規制・リスク", "risk",
     ["source weight +12", "agent", "risk", "fresh"],
     "OpenAI's Codex now encrypts the internal instructions exchanged between AI agents, so developers see only unreadable strings and can no longer trace how tasks get delegated between sub-agents."),
    ("Hack suggests AI music generator Suno scraped YouTube for training data",
     "https://techcrunch.com/2026/07/15/hack-suggests-ai-music-generator-suno-scraped-youtube-for-training-data/",
     "TechCrunch AI", 16, "2026-07-15", "SEEN", 17,
     "規制・リスク、市場動向", "risk",
     ["source weight +16", "risk", "legal", "market", "fresh"],
     "A supply-chain hack exposed AI music generator Suno's source code, suggesting the company scraped decades of audio from YouTube Music, Deezer, Genius, stock libraries, and podcast feeds for training data."),
    ("German AI consortium releases Soofi S, an open 30B model that tops benchmarks in both English and German",
     "https://the-decoder.com/german-ai-consortium-releases-soofi-s-an-open-30b-model-that-tops-benchmarks-in-both-english-and-german/",
     "The Decoder", 12, "2026-07-15", "SEEN", 14,
     "モデル/API", "model",
     ["source weight +12", "model", "open source", "fresh"],
     "A German research consortium released Soofi S, an open-source model using a resource-efficient hybrid architecture that activates only 3.2 of its 31.6 billion parameters per token, topping benchmarks in both English and German."),
    ("Google Releases LiteRT.js: A JavaScript Binding of LiteRT That Runs .tflite Models in Browsers via WebGPU",
     "https://www.marktechpost.com/2026/07/15/google-releases-litert-js-a-javascript-binding-of-litert-that-runs-tflite-models-in-browsers-via-webgpu/",
     "MarkTechPost", 8, "2026-07-15", "SEEN", 12,
     "モデル/API、開発者ツール", "platform",
     ["source weight +8", "model", "developer", "open source", "fresh"],
     "Google released LiteRT.js, a JavaScript binding running .tflite models directly in the browser via WebGPU, CPU (XNNPACK), or the experimental WebNN API — up to 3x faster than other web runtimes for local, zero-server-cost inference."),
    ("TSMC posts record quarter as AI chip demand pushes full-year growth outlook past 40%",
     "https://www.techtimes.com/articles/320696/20260716/tsmc-posts-record-quarter-ai-chip-demand-pushes-full-year-growth-outlook-past-40.htm",
     "Tech Times", 4, "2026-07-16", "SEEN", 38,
     "市場動向", "market",
     ["source weight +4", "market", "compute", "fresh"],
     "TSMC posted record Q2 2026 revenue of $40.2 billion, up 36% year over year, with net profit surging 77.4% on AI-driven High Performance Computing demand (now 66% of revenue). CEO C.C. Wei announced an additional $100 billion Arizona investment and raised 2026 capex guidance to $60-64 billion."),
    ("Kimi's open model K3 nears GPT-5.6 Sol and Fable 5 while signaling the end of super cheap Chinese AI",
     "https://the-decoder.com/kimis-open-model-k3-nears-gpt-5-6-sol-and-fable-5-while-signaling-the-end-of-super-cheap-chinese-ai/",
     "The Decoder", 12, "2026-07-16", "SEEN", 35,
     "モデル/API、市場動向", "model",
     ["source weight +12", "model", "open source", "market", "fresh"],
     "Kimi released K3, a multimodal open-weight MoE model with 896 experts, 2.8 trillion total parameters, and a 1M-token context window. Kimi's own benchmarks put it close to Claude Fable 5 and GPT-5.6 Sol, beating other tested systems by a wide margin — while its higher training cost signals the era of ultra-cheap Chinese models may be ending."),
    ("Microsoft July 2026 Patch Tuesday fixes record 570 flaws as AI-powered scanning finds bugs before attackers do",
     "https://www.bleepingcomputer.com/news/microsoft/microsoft-july-2026-patch-tuesday-fixes-massive-570-flaws-3-zero-days/",
     "BleepingComputer", 4, "2026-07-14", "SEEN", 32,
     "規制・リスク、モデル/API", "risk",
     ["source weight +4", "risk", "security", "model", "fresh"],
     "Microsoft's July 2026 Patch Tuesday fixed a record 570 flaws, including three zero-days (two actively exploited), with the company crediting a newly deployed AI-powered vulnerability-discovery system for proactively scanning the Windows codebase before threat actors could."),
    ("xAI open-sources \"Grok-Build\" on GitHub after massive data breach",
     "https://the-decoder.com/xai-open-sources-grok-build-on-github-after-massive-data-breach/",
     "The Decoder", 12, "2026-07-16", "SEEN", 30,
     "規制・リスク、AIエージェント", "risk",
     ["source weight +12", "risk", "agent", "security", "fresh"],
     "xAI's coding agent Grok Build drew heavy criticism after users discovered it uploaded entire directories — including SSH keys, password databases, and personal photos — to xAI's Google Cloud servers. xAI disabled the upload feature and open-sourced Grok Build's full source code under Apache 2.0 to rebuild trust."),
    ("OpenAI wants developers to stop typing commands and start using a joystick to control their AI agents",
     "https://the-decoder.com/openai-wants-developers-to-stop-typing-commands-and-start-using-a-joystick-to-control-their-ai-agents/",
     "The Decoder", 12, "2026-07-16", "SEEN", 24,
     "AIエージェント、モデル/API", "agent",
     ["source weight +12", "agent", "model", "fresh"],
     "OpenAI and keyboard maker Work Louder unveiled Codex Micro, a compact hardware controller with joysticks and a rotary dial that lets developers manage AI agents without constantly switching windows and typing commands."),
    ("Anthropic extends free Fable 5 access for subscribers as OpenAI's GPT-5.6 Sol heats up the pricing war",
     "https://the-decoder.com/anthropic-extends-free-fable-5-access-for-subscribers-as-openais-gpt-5-6-sol-heats-up-the-pricing-war/",
     "The Decoder", 12, "2026-07-16", "SEEN", 23,
     "モデル/API、市場動向", "model",
     ["source weight +12", "model", "market", "fresh"],
     "Anthropic extended free Fable 5 access for subscribers as OpenAI's GPT-5.6 Sol intensifies the frontier-model pricing war, the latest move in a market now spanning five actively competing API tiers."),
    ("AI-powered travel agency Fora hits unicorn status, raises $60M",
     "https://techcrunch.com/2026/07/16/ai-powered-travel-agency-fora-hits-unicorn-status-raises-60m/",
     "TechCrunch AI", 16, "2026-07-16", "SEEN", 21,
     "資金調達、市場動向", "market",
     ["source weight +16", "funding", "market", "fresh"],
     "Travel agency Fora raised a $60 million Series D led by Forerunner and Tactile Ventures at a $1 billion valuation, with funds expanding its AI assistant Via, which helps human travel agents with research and itinerary building."),
    ("Gemini 3.5: frontier intelligence with action",
     "https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-5/",
     "Google AI Blog", 16, "2026-07-17", "SEEN", 53,
     "モデル/API、市場動向", "model",
     ["source weight +16", "model", "launch", "market", "fresh"],
     "Google confirmed Gemini 3.5 Pro's launch on July 17 with a 2-million-token context window, a new 'Deep Think' reasoning mode available on the $250/month Ultra tier, and meaningful gains in coding and long-horizon reasoning over Gemini 3.0 — after repeated delays and a reported scrap-and-rebuild following structural failures in recursive tool-calling."),
    ("China's Xi says AI 'should not be a solo performance by a single country'",
     "https://www.aljazeera.com/news/2026/7/17/ai-xi",
     "Al Jazeera", 8, "2026-07-17", "SEEN", 49,
     "規制・リスク、市場動向", "risk",
     ["source weight +8", "governance", "risk", "market", "fresh"],
     "In his first-ever keynote at Shanghai's World AI Conference, Xi Jinping said AI development 'should not be a solo performance by any single country but rather a symphony of global cooperation,' pitching a China-led vision for global AI governance the same day Google launched Gemini 3.5 Pro."),
    ("Just like Deepseek, China's Kimi K3 is forcing Western AI labs to question their compute advantage",
     "https://the-decoder.com/just-like-deepseek-chinas-kimi-k3-is-forcing-western-ai-labs-to-question-their-compute-advantage/",
     "The Decoder", 12, "2026-07-17", "SEEN", 40,
     "モデル/API、市場動向", "model",
     ["source weight +12", "model", "market", "open source", "fresh"],
     "Moonshot AI shipped Kimi K3 Max and K3 Swarm Max hours before Google's Gemini 3.5 Pro launch, at $3 input/$15 output per million tokens with open weights promised by July 27 — guaranteeing every Gemini benchmark gets compared against a Chinese model and reviving doubts about whether US export controls are working."),
    ("OpenAI Details GPT-Red: An Internal Automated Red-Teaming Model That Beat Human Red-Teamers 84% To 13% On Prompt Injection",
     "https://www.marktechpost.com/2026/07/16/openai-details-gpt-red-an-internal-automated-red-teaming-model-that-beat-human-red-teamers-84-to-13-on-prompt-injection/",
     "MarkTechPost", 8, "2026-07-16", "SEEN", 31,
     "モデル/API、規制・リスク、研究", "risk",
     ["source weight +8", "model", "security", "research", "fresh"],
     "OpenAI detailed GPT-Red, an internal-only automated red-teaming model trained via self-play to discover prompt-injection vulnerabilities. In tests it attacked models successfully 84% of the time versus 13% for human red-teamers, including manipulating an AI-operated vending machine into selling a $100+ item for $0.50."),
    ("Netflix's 300 AI productions show how fast the technology is spreading through entertainment",
     "https://the-decoder.com/netflixs-300-ai-productions-show-how-fast-the-technology-is-spreading-through-entertainment/",
     "The Decoder", 12, "2026-07-17", "SEEN", 22,
     "市場動向", "market",
     ["source weight +12", "market", "fresh"],
     "Netflix co-CEO Ted Sarandos disclosed that AI is now used in about 300 productions, mostly in post-production work like expanding crowd scenes and historical battle sequences that would otherwise have been cut for budget or time."),
    ("NVIDIA AI Releases Nemotron 3 Embed: An Open Embedding Collection Whose 8B Checkpoint Ranks #1 on RTEB",
     "https://www.marktechpost.com/2026/07/17/nvidia-ai-releases-nemotron-3-embed-an-open-embedding-collection-whose-8b-checkpoint-ranks-1-on-rteb/",
     "MarkTechPost", 8, "2026-07-17", "SEEN", 17,
     "モデル/API", "model",
     ["source weight +8", "model", "open source", "benchmark", "fresh"],
     "NVIDIA released Nemotron 3 Embed, three open embedding checkpoints under OpenMDW-1.1, with the 8B version ranking #1 on the Retrieval Embedding Benchmark (RTEB) at a score of 78.46."),
    ("Anthropic slashes Claude Fable 5 limits in Max and Team Premium and pushes Pro users toward API pricing",
     "https://the-decoder.com/anthropic-slashes-claude-fable-5-limits-in-max-and-team-premium-and-pushes-pro-users-toward-api-pricing/",
     "The Decoder", 12, "2026-07-18", "NEW", 45,
     "モデル/API、法人導入、市場動向", "market",
     ["source weight +12", "model", "enterprise", "market", "fresh"],
     "Starting July 20, Claude Fable 5 will be included in all Max and Team Premium plans but with regular limits cut 33% and Fable 5 capped at half of that. Pro and Team Standard subscribers effectively lose access, getting a one-time $100 usage credit before facing API pricing — a reversal widely read as a response to OpenAI's similarly capable, one-third-the-cost GPT-5.6 Sol."),
    ("China's Xi Jinping launches new AI alliance: What is it?",
     "https://www.aljazeera.com/news/2026/7/17/chinas-xi-jinping-launches-new-ai-alliance-what-is-it",
     "Al Jazeera", 8, "2026-07-17", "NEW", 39,
     "規制・リスク、市場動向", "risk",
     ["source weight +8", "governance", "risk", "market", "fresh"],
     "China formally established the World AI Cooperation Organization on July 16 with 29 founding member countries including Indonesia, Brazil, Malaysia, South Africa, Senegal, Russia, and Pakistan — a Shanghai-headquartered body positioned as an alternative venue for international AI governance."),
    ("We Just Had The First Humanoid Robot Strike Ever",
     "https://www.forbes.com/sites/johnkoetsier/2026/07/17/we-just-had-the-first-humanoid-robot-strike-ever/",
     "Forbes", 8, "2026-07-17", "NEW", 35,
     "規制・リスク、市場動向", "risk",
     ["source weight +8", "risk", "market", "labor", "fresh"],
     "Hyundai Motor workers held a three-day partial strike, demanding formal negotiation rights and income guarantees before any deployment of the company's Atlas humanoid robots, plus larger bonuses — a labor response widely described as the first strike explicitly triggered by humanoid-robot job-security fears."),
    ("Google Cloud's Always-On Memory Agent Replaces RAG and Embeddings With Continuous LLM Consolidation on Gemini 3.1 Flash-Lite",
     "https://www.marktechpost.com/2026/07/18/google-clouds-always-on-memory-agent-replaces-rag-and-embeddings-with-continuous-llm-consolidation-on-gemini-3-1-flash-lite/",
     "MarkTechPost", 8, "2026-07-18", "NEW", 22,
     "AIエージェント、モデル/API", "agent",
     ["source weight +8", "agent", "model", "open source", "fresh"],
     "Google Cloud published a reference agent that treats memory as a running process rather than a RAG pipeline: it runs continuously on Google ADK and Gemini 3.1 Flash-Lite, using no vector database or embeddings — instead an LLM reads, thinks, and writes structured memory directly into SQLite via three specialist sub-agents."),
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
