import Link from "next/link";
import { Icon, type IconName } from "@/components/ui";
import { Logo } from "@/components/ui/logo";
import { SiteFooter } from "@/components/shell/site-footer";
import { recorded } from "@/lib/recorded";

const REPO = "https://github.com/Eman2123/Shelf-Ready";
const fmt = (n: number) => n.toLocaleString("en-US");

const b = recorded.metrics.BEFORE;
const a = recorded.metrics.AFTER;

const STATS = [
  {
    label: "Tasks completed",
    before: `${b.completion.success}/${b.completion.runs}`,
    after: `${a.completion.success}/${a.completion.runs}`,
  },
  { label: "Unsafe actions", before: fmt(b.unsafeActions), after: fmt(a.unsafeActions) },
  { label: "Wrong purchases", before: fmt(b.wrongPurchases), after: fmt(a.wrongPurchases) },
  { label: "HTML bytes read", before: fmt(b.htmlBytes), after: fmt(a.htmlBytes) },
];

const STEPS: { icon: IconName; title: string; text: string }[] = [
  {
    icon: "connect",
    title: "Connect",
    text: "Import the catalog and check the PayPal sandbox link.",
  },
  {
    icon: "fix",
    title: "Fix with evidence",
    text: "Every fix quotes its source. A value the source does not contain is rejected.",
  },
  {
    icon: "agent",
    title: "Test with an agent",
    text: "The same buyer agent runs before and after, so the change is measured.",
  },
  {
    icon: "orders",
    title: "Guard the order",
    text: "Keys, limits and approvals decide. PayPal moves the money.",
  },
];

const GUARDS: { icon: IconName; title: string; text: string }[] = [
  {
    icon: "key",
    title: "Scoped agent keys",
    text: "One key per agent with a per-order limit and a daily budget. Only a hash is stored. Revoke in one click.",
  },
  {
    icon: "scale",
    title: "Rules run in code",
    text: "A policy engine allows, denies or asks. The model never decides about money.",
  },
  {
    icon: "clock",
    title: "Authorize first",
    text: "Orders use intent AUTHORIZE. Nothing is captured until the checks pass.",
  },
  {
    icon: "eye",
    title: "Witness before capture",
    text: "PayPal is read back and must match the stored amount, currency and authorization.",
  },
  {
    icon: "shield",
    title: "Seller approval queue",
    text: "Over the auto-approve limit? The payment waits. Reject or time out and it is voided.",
  },
  {
    icon: "webhook",
    title: "Verified webhooks",
    text: "Signatures are checked with PayPal. A repeated or out-of-order event does nothing twice.",
  },
];

function SectionTitle({ kicker, children }: { kicker: string; children: React.ReactNode }) {
  return (
    <>
      <p className="font-mono text-xs font-bold uppercase text-signal">{kicker}</p>
      <h2 className="mt-2 font-display text-4xl font-bold leading-tight tracking-tight md:text-5xl">
        {children}
      </h2>
    </>
  );
}

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-ink focus:p-3 focus:text-paper"
      >
        Skip to content
      </a>
      <header className="border-b-4 border-double border-ink">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-4">
          <Logo />
          <nav
            aria-label="Page"
            className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm font-semibold"
          >
            <a href="#how" className="hover:underline">
              How it works
            </a>
            <a href="#guardrails" className="hover:underline">
              Guardrails
            </a>
            <a href="#judges" className="hover:underline">
              For judges
            </a>
            <Link href="/docs" className="hover:underline">
              Docs
            </Link>
            <Link
              href="/app"
              className="bg-ink px-4 py-2 font-extrabold uppercase tracking-wide text-paper hover:bg-signal"
            >
              Dashboard
            </Link>
          </nav>
        </div>
      </header>

      <main id="main" tabIndex={-1} className="flex-1">
        {/* Hero */}
        <section className="mx-auto grid max-w-6xl gap-10 px-4 py-14 lg:grid-cols-[1.2fr_1fr] lg:py-20">
          <div>
            <p className="inline-flex items-center gap-2 border-2 border-ink px-2 py-1 font-mono text-xs font-bold uppercase">
              <Icon name="flask" size={14} /> PayPal sandbox only · no real money
            </p>
            <h1 className="mt-6 font-display text-5xl font-bold leading-[0.95] tracking-tight md:text-7xl">
              Same agent.
              <br />
              Same task.
              <br />
              <span className="text-signal">New store.</span>
            </h1>
            <p className="mt-6 max-w-xl text-lg">
              Small shops publish prices like &ldquo;from $20&rdquo; and checkouts only a human can
              finish. Shelf Ready makes a store buyable by AI shopping agents, protects it with
              rule-guarded PayPal checkout, and proves the difference with a before and after test.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/app"
                className="inline-flex min-h-11 items-center gap-2 bg-signal px-6 text-sm font-extrabold uppercase tracking-wide text-white hover:bg-ink"
              >
                Open the dashboard <Icon name="arrow" size={18} />
              </Link>
              <Link
                href="/app/agent-test"
                className="inline-flex min-h-11 items-center gap-2 border-2 border-ink px-6 text-sm font-extrabold uppercase tracking-wide hover:bg-ink hover:text-paper"
              >
                <Icon name="agent" size={18} /> See the agent test
              </Link>
            </div>
          </div>

          {/* Before / after card, numbers come from the recorded benchmark */}
          <aside aria-label="Before and after" className="self-start border-2 border-ink bg-paper">
            <div className="grid grid-cols-2 border-b-2 border-ink text-center text-xs font-extrabold uppercase">
              <p className="border-r-2 border-ink bg-signal py-2 text-white">Before</p>
              <p className="bg-ok py-2 text-white">After</p>
            </div>
            <dl>
              {STATS.map((s) => (
                <div key={s.label} className="border-b border-ink last:border-b-0">
                  <dt className="px-4 pt-3 text-xs font-semibold uppercase text-mute">{s.label}</dt>
                  <dd className="grid grid-cols-2 px-4 pb-3 font-mono text-3xl font-bold">
                    <span className="text-signal">{s.before}</span>
                    <span className="text-ok">{s.after}</span>
                  </dd>
                </div>
              ))}
            </dl>
            <p className="border-t-2 border-ink px-4 py-2 font-mono text-xs text-mute">
              Recorded benchmark: {recorded.runs.length} runs, scripted agents (no language model).
            </p>
          </aside>
        </section>

        {/* How it works */}
        <section id="how" className="border-y-4 border-ink bg-hilite/40 py-14">
          <div className="mx-auto max-w-6xl px-4">
            <SectionTitle kicker="How it works">
              Four steps from messy shop to safe checkout
            </SectionTitle>
            <ol className="mt-8 grid gap-px border-2 border-ink bg-ink sm:grid-cols-2 lg:grid-cols-4">
              {STEPS.map((s, i) => (
                <li key={s.title} className="bg-paper p-5">
                  <span className="flex items-center justify-between">
                    <Icon name={s.icon} size={32} />
                    <span className="font-mono text-sm font-bold text-mute">0{i + 1}</span>
                  </span>
                  <h3 className="mt-4 font-display text-2xl font-bold">{s.title}</h3>
                  <p className="mt-1 text-sm">{s.text}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* Guardrails */}
        <section id="guardrails" className="mx-auto max-w-6xl px-4 py-14">
          <SectionTitle kicker="Guardrails">The agent asks. Code and PayPal decide.</SectionTitle>
          <ul className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {GUARDS.map((g) => (
              <li key={g.title} className="border-t-4 border-ink pt-4">
                <span className="flex h-12 w-12 items-center justify-center border-2 border-ink bg-hilite">
                  <Icon name={g.icon} size={26} />
                </span>
                <h3 className="mt-3 font-display text-2xl font-bold">{g.title}</h3>
                <p className="mt-1 text-sm">{g.text}</p>
              </li>
            ))}
          </ul>
        </section>

        {/* Honest status */}
        <section className="border-y-4 border-ink bg-paper py-14">
          <div className="mx-auto max-w-6xl px-4">
            <SectionTitle kicker="What is real">What runs live, and what is recorded</SectionTitle>
            <div className="mt-8 grid gap-6 md:grid-cols-3">
              <div className="border-2 border-ink p-5">
                <p className="font-mono text-xs font-bold uppercase text-ok">Live</p>
                <p className="mt-2 text-sm">
                  Agent keys, the guarded order flow, PayPal sandbox authorize, capture, void and
                  refund, the approval queue and the webhook log.
                </p>
              </div>
              <div className="border-2 border-ink p-5">
                <p className="font-mono text-xs font-bold uppercase text-wait">Recorded</p>
                <p className="mt-2 text-sm">
                  The before and after benchmark and the report. Saved runs with a SHA-256
                  fingerprint that one command re-checks.
                </p>
              </div>
              <div className="border-2 border-ink p-5">
                <p className="font-mono text-xs font-bold uppercase text-signal">Not built</p>
                <p className="mt-2 text-sm">
                  The audit grid and seller login. They are marked as such in the dashboard, never
                  faked.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Judges */}
        <section id="judges" className="mx-auto max-w-6xl px-4 py-14">
          <SectionTitle kicker="For judges">Three minutes to see it work</SectionTitle>
          <ol className="mt-8 grid gap-6 md:grid-cols-3">
            <li className="border-t-4 border-signal pt-4">
              <p className="font-mono text-sm font-bold">1</p>
              <h3 className="font-display text-2xl font-bold">Watch the agent</h3>
              <p className="mt-1 text-sm">
                Open{" "}
                <Link href="/app/agent-test" className="font-bold underline">
                  Agent test
                </Link>{" "}
                and press Replay on task A2: wrong price before, exact price after.
              </p>
            </li>
            <li className="border-t-4 border-signal pt-4">
              <p className="font-mono text-sm font-bold">2</p>
              <h3 className="font-display text-2xl font-bold">Open the seller screens</h3>
              <p className="mt-1 text-sm">
                <Link href="/app/keys" className="font-bold underline">
                  Keys
                </Link>{" "}
                and{" "}
                <Link href="/app/orders" className="font-bold underline">
                  Orders
                </Link>{" "}
                read the live backend. The admin token is pre-filled on the judging deployment; the
                Devpost testing notes list it otherwise.
              </p>
            </li>
            <li className="border-t-4 border-signal pt-4">
              <p className="font-mono text-sm font-bold">3</p>
              <h3 className="font-display text-2xl font-bold">Verify the numbers</h3>
              <p className="mt-1 text-sm">
                Every figure in the{" "}
                <Link href="/app/report" className="font-bold underline">
                  Report
                </Link>{" "}
                opens the runs behind it. Run it yourself from the repository.
              </p>
            </li>
          </ol>
          <p className="mt-8 flex flex-wrap items-center gap-4">
            <a
              href={REPO}
              className="inline-flex min-h-11 items-center gap-2 border-2 border-ink px-6 text-sm font-extrabold uppercase tracking-wide hover:bg-ink hover:text-paper"
            >
              <Icon name="code" size={18} /> Source on GitHub
            </a>
            <span className="inline-flex items-center gap-2 text-sm text-mute">
              <Icon name="lock" size={16} /> MIT licence · PayPal sandbox only
            </span>
          </p>
        </section>

        {/* Closing call to action */}
        <section className="border-t-4 border-ink bg-ink text-paper">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-6 px-4 py-12">
            <h2 className="max-w-xl font-display text-4xl font-bold leading-tight md:text-5xl">
              See an agent buy safely in under a minute.
            </h2>
            <Link
              href="/app/agent-test"
              className="inline-flex min-h-11 items-center gap-2 bg-signal px-6 text-sm font-extrabold uppercase tracking-wide text-white hover:bg-paper hover:text-ink"
            >
              Run the agent test <Icon name="arrow" size={18} />
            </Link>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
