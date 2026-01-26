import ChatPanel from "./components/ChatPanel";
import {
  bountyTemplates,
  howItWorks,
  proofGuidelines,
  ramusVoice,
} from "./content/ramus";

const POIDH_ACCOUNT = import.meta.env.VITE_POIDH_ACCOUNT as string | undefined;
const POIDH_URL = POIDH_ACCOUNT
  ? `https://poidh.xyz/account/${POIDH_ACCOUNT}`
  : "https://poidh.xyz";

export default function App() {
  return (
    <div className="app">
      <header className="hero" id="home">
        <nav className="nav">
          <div className="logo">RAMUS</div>
          <div className="nav__links">
            <a href="#how">How It Works</a>
            <a href="#bounties">Live Bounties</a>
            <a href="#proof">Proof</a>
            <a href="#chat">Chat</a>
          </div>
        </nav>
        <div className="hero__content">
          <div>
            <p className="eyebrow">Ancient tree god of renewal</p>
            <h1>{ramusVoice.title}</h1>
            <p className="lead">{ramusVoice.subtitle}</p>
            <p className="invocation">“{ramusVoice.invocation}”</p>
            <div className="hero__actions">
              <a className="button" href="#chat">
                {ramusVoice.cta}
              </a>
              <a className="button button--ghost" href="#bounties">
                See live bounties
              </a>
            </div>
          </div>
          <div className="hero__card">
            <h2>Ramus Vow</h2>
            <p>
              I reward those who tend the commons. Pick up trash, restore a
              space, and leave proof. My roots pay promptly.
            </p>
            <div className="sigil">♣</div>
          </div>
        </div>
      </header>

      <main>
        <section className="section" id="how">
          <h2>How It Works</h2>
          <div className="grid">
            {howItWorks.map((step) => (
              <article key={step.title} className="card">
                <h3>{step.title}</h3>
                <p>{step.detail}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="section" id="bounties">
          <div className="section__header">
            <h2>Live Bounties</h2>
            <p>Examples of what Ramus posts in the wild.</p>
          </div>
          <div className="grid grid--tight">
            {bountyTemplates.map((bounty) => (
              <article key={bounty.name} className="card card--glow">
                <h3>{bounty.name}</h3>
                <p>{bounty.prompt}</p>
                <span className="tag">Real-world action</span>
              </article>
            ))}
          </div>
        </section>

        <section className="section" id="proof">
          <div className="section__header">
            <h2>Proof Requirements</h2>
            <p>Ramus honors clear evidence. Keep it simple and honest.</p>
          </div>
          <ul className="rules">
            {proofGuidelines.map((rule) => (
              <li key={rule}>{rule}</li>
            ))}
          </ul>
        </section>

        <section className="section" id="chat">
          <ChatPanel />
        </section>
      </main>

      <footer className="footer">
        <div>
          <strong>Ramus</strong> • tending the commons with autonomous bounties.
        </div>
        <div className="footer__links">
          <span>ramus.ai</span>
          <a href={POIDH_URL} target="_blank" rel="noreferrer">
            POIDH account
          </a>
          <span>XMTP</span>
        </div>
      </footer>
    </div>
  );
}
