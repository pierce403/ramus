import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Client,
  ConsentState,
  DecodedMessage,
  IdentifierKind,
  type Conversation,
  type Signer,
} from "@xmtp/browser-sdk";
import { BrowserProvider, getBytes } from "ethers";

const BOT_ADDRESS = import.meta.env.VITE_XMTP_BOT_ADDRESS as string | undefined;
const XMTP_ENV = (import.meta.env.VITE_XMTP_ENV as string | undefined) ?? "production";

const ENCRYPTION_KEY_STORAGE = "ramus_xmtp_key";

function getOrCreateEncryptionKey(): Uint8Array {
  const stored = localStorage.getItem(ENCRYPTION_KEY_STORAGE);
  if (stored) {
    return getBytes(stored);
  }
  const key = crypto.getRandomValues(new Uint8Array(32));
  const keyHex = `0x${Array.from(key).map((b) => b.toString(16).padStart(2, "0")).join("")}`;
  localStorage.setItem(ENCRYPTION_KEY_STORAGE, keyHex);
  return key;
}

async function createSigner(): Promise<Signer> {
  if (!window.ethereum) {
    throw new Error("No injected wallet found.");
  }
  const provider = new BrowserProvider(window.ethereum);
  await provider.send("eth_requestAccounts", []);
  const signer = await provider.getSigner();
  const address = (await signer.getAddress()).toLowerCase();
  return {
    type: "EOA",
    getIdentifier: () => ({ identifier: address, identifierKind: IdentifierKind.Ethereum }),
    signMessage: async (message: string) => {
      const signature = await signer.signMessage(message);
      return getBytes(signature);
    },
  };
}

export default function ChatPanel() {
  const [client, setClient] = useState<Client | null>(null);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<DecodedMessage[]>([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState("disconnected");
  const isReady = useMemo(() => !!client && !!conversation, [client, conversation]);

  const connect = useCallback(async () => {
    if (!BOT_ADDRESS) {
      setStatus("Missing VITE_XMTP_BOT_ADDRESS");
      return;
    }
    setStatus("connecting");
    const signer = await createSigner();
    const key = getOrCreateEncryptionKey();
    const newClient = await Client.create(signer, key, { env: XMTP_ENV });
    const dm = await newClient.conversations.newDmWithIdentifier({
      identifier: BOT_ADDRESS.toLowerCase(),
      identifierKind: IdentifierKind.Ethereum,
    });
    const consent = await dm.consentState();
    if (consent !== ConsentState.ALLOWED) {
      await dm.updateConsentState(ConsentState.ALLOWED);
    }
    const history = await dm.messages();
    setMessages(history);
    setClient(newClient);
    setConversation(dm);
    setStatus("connected");
  }, []);

  const sendMessage = useCallback(async () => {
    if (!conversation || !input.trim()) {
      return;
    }
    await conversation.send(input.trim());
    setInput("");
  }, [conversation, input]);

  useEffect(() => {
    let isMounted = true;
    let stream: { return: (value?: DecodedMessage) => Promise<unknown> } | null = null;

    const startStream = async () => {
      if (!conversation) {
        return;
      }
      stream = await conversation.stream();
      for await (const message of stream) {
        if (!isMounted || !message) {
          break;
        }
        setMessages((prev) => [...prev, message]);
      }
    };

    startStream();

    return () => {
      isMounted = false;
      if (stream) {
        void stream.return();
      }
    };
  }, [conversation]);

  return (
    <section className="chat">
      <header>
        <h3>Speak with Ramus</h3>
        <p>Connect your wallet to open a direct line to the grove.</p>
      </header>
      <div className="chat__panel">
        {!isReady ? (
          <button className="button" onClick={connect}>
            Connect XMTP
          </button>
        ) : (
          <div className="chat__body">
            <div className="chat__messages">
              {messages.map((message) => (
                <div key={message.id} className="chat__message">
                  <span>{String(message.content)}</span>
                </div>
              ))}
            </div>
            <div className="chat__input">
              <input
                type="text"
                placeholder="Ask Ramus for a bounty or status"
                value={input}
                onChange={(event) => setInput(event.target.value)}
              />
              <button className="button" onClick={sendMessage}>
                Send
              </button>
            </div>
          </div>
        )}
        <footer>Status: {status}</footer>
      </div>
    </section>
  );
}
