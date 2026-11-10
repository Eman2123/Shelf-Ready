import { Figure } from "@/components/report/figure";
import { StatusTag } from "@/components/ui";
import { recorded } from "@/lib/recorded";
import { benchmarkMetrics, safetySummary, taskRows, variantSummary } from "@/lib/report";

function Section({ n, title, children }: { n: string; title: string; children: React.ReactNode }) {
  return (
    <section className="mt-10 border-t-4 border-double border-ink pt-4">
      <h2 className="font-display text-3xl font-bold tracking-tight">
        <span data-static className="mr-3 font-mono text-base font-normal">
          {n}
        </span>
        {title}
      </h2>
      {children}
    </section>
  );
}

/** A section whose numbers come from a part of the system that is not connected yet. */
function NotConnected({ what, from }: { what: string; from: string }) {
  return (
    <p className="mt-3 border border-dashed border-ink p-4 text-sm">
      <StatusTag kind="wait">Not connected</StatusTag>{" "}
      <span>
        {what} is not shown here because no real run exists yet. It will appear with its run id when
        the {from} is connected. No number is made up in its place.
      </span>
    </p>
  );
}

export function ReportView() {
  const metrics = benchmarkMetrics();
  const tasks = taskRows();
  const safety = safetySummary();
  const variants = variantSummary();
  return (
    <div>
      <p className="border-b-4 border-double border-ink pb-2 font-mono text-xs font-bold uppercase">
        Readiness Receipt · Tidewell Goods (fictional) · PayPal sandbox only
      </p>
      <p className="mt-3 max-w-2xl text-sm">
        Every number below opens the runs it came from and their raw record. Agents here are the
        scripted baselines named in each run, not a language model.
      </p>

      <Section n="01" title="Readiness score, before and after">
        <NotConnected what="The readiness score and its waterfall" from="audit engine" />
      </Section>

      <Section n="02" title="Agent benchmark">
        <p className="mt-2 text-sm">
          The same <span data-static>{recorded.tasks.length}</span> tasks, run{" "}
          <span data-static>{recorded.k}</span> times each, before and after the store is made
          agent-ready.
        </p>
        <div className="relative mt-4 overflow-x-auto">
          <table className="w-full min-w-[34rem] border-collapse text-left text-sm">
            <caption className="sr-only">Benchmark totals, before and after</caption>
            <thead>
              <tr className="border-b-2 border-ink font-mono text-xs uppercase">
                <th scope="col" className="py-2 pr-4">
                  Measure
                </th>
                <th scope="col" className="py-2 pr-4">
                  Before
                </th>
                <th scope="col" className="py-2 pr-4">
                  After
                </th>
              </tr>
            </thead>
            <tbody>
              {metrics.map((m) => (
                <tr key={m.label} className="border-b border-ink align-top">
                  <th scope="row" className="py-3 pr-4 font-semibold">
                    {m.label}
                    <span data-static className="block text-xs font-normal text-mute">
                      {m.note}
                    </span>
                  </th>
                  <td className="py-3 pr-4">
                    <Figure fig={m.before} />
                  </td>
                  <td className="py-3 pr-4">
                    <Figure fig={m.after} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3 className="mt-8 font-display text-xl font-bold">Per task, runs that succeeded</h3>
        <div className="relative mt-2 overflow-x-auto">
          <table className="w-full min-w-[34rem] border-collapse text-left text-sm">
            <caption className="sr-only">Per-task results, before and after</caption>
            <thead>
              <tr className="border-b-2 border-ink font-mono text-xs uppercase">
                <th scope="col" className="py-2 pr-4">
                  Task
                </th>
                <th scope="col" className="py-2 pr-4">
                  Before
                </th>
                <th scope="col" className="py-2 pr-4">
                  After
                </th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((t) => (
                <tr key={t.id} className="border-b border-ink align-top">
                  <th scope="row" className="py-2 pr-4 font-normal">
                    <span data-static>{t.title}</span>
                    <span data-static className="block font-mono text-xs text-mute">
                      expected {t.expected}
                    </span>
                  </th>
                  <td className="py-2 pr-4">
                    <Figure fig={t.before} />
                  </td>
                  <td className="py-2 pr-4">
                    <Figure fig={t.after} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section n="03" title="Defect variants">
        <p className="mt-2 max-w-2xl text-sm">
          <span data-static className="font-mono font-bold">
            {variants.label}
          </span>
          : five hand-built pages of one product, each with one defect. A scripted page reader (no
          LLM) must read an exact price, a stock statement and a shipping cost, and must ignore any
          instruction written on the page. These are five pages, not a sample, so no link between
          readiness score and pass rate is claimed.
        </p>
        <p className="mt-2 text-sm">
          Pages passed: <Figure fig={variants.passRate} />
        </p>
        <div className="relative mt-4 overflow-x-auto">
          <table className="w-full min-w-[34rem] border-collapse text-left text-sm">
            <caption className="sr-only">Defect variant results</caption>
            <thead>
              <tr className="border-b-2 border-ink font-mono text-xs uppercase">
                <th scope="col" className="py-2 pr-4">
                  Variant
                </th>
                <th scope="col" className="py-2 pr-4">
                  Readiness score
                </th>
                <th scope="col" className="py-2 pr-4">
                  Reader result
                </th>
                <th scope="col" className="py-2 pr-4">
                  Why
                </th>
              </tr>
            </thead>
            <tbody>
              {variants.rows.map((v) => (
                <tr key={v.variant} className="border-b border-ink align-top">
                  <th scope="row" data-static className="py-2 pr-4 font-normal">
                    {v.title}
                  </th>
                  <td className="py-2 pr-4">
                    <StatusTag kind="wait">Not connected</StatusTag>
                  </td>
                  <td className="py-2 pr-4">
                    <Figure fig={v.result} />
                  </td>
                  <td data-static className="py-2 pr-4">
                    {v.reason}
                    {v.injectionPresent ? ". Page text told the reader to place an order." : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <NotConnected what="The readiness score of each variant" from="audit engine" />
      </Section>

      <Section n="04" title="Issues found, fixed, and needing the seller">
        <NotConnected what="Issue and fix counts" from="audit and fix engine" />
      </Section>

      <Section n="05" title="Unsupported facts introduced">
        <NotConnected what="The unsupported-facts count for the whole catalog" from="fix engine" />
      </Section>

      <Section n="06" title="Policy, injection and PayPal">
        <dl className="mt-3 grid gap-6 sm:grid-cols-2">
          <div className="border border-ink p-4">
            <dt className="font-semibold">
              Policy tests (limits, quantity, category, budget, key)
            </dt>
            <dd className="mt-2 flex gap-8">
              <span>
                <span className="block text-xs text-mute">Before</span>
                <Figure fig={safety.policy.before} />
              </span>
              <span>
                <span className="block text-xs text-mute">After</span>
                <Figure fig={safety.policy.after} />
              </span>
            </dd>
          </div>
          <div className="border border-ink p-4">
            <dt className="font-semibold">Injection test (text inside a product description)</dt>
            <dd className="mt-2 flex gap-8">
              <span>
                <span className="block text-xs text-mute">Before</span>
                <Figure fig={safety.injection.before} />
              </span>
              <span>
                <span className="block text-xs text-mute">After</span>
                <Figure fig={safety.injection.after} />
              </span>
            </dd>
          </div>
        </dl>
        <p className="mt-4 text-sm">
          The store stops unsafe orders in its own code. The checks above ran against a stand-in for
          the money guard; they are re-run against the real one when it is connected.
        </p>
        <NotConnected what="PayPal sandbox verification" from="PayPal checkout" />
      </Section>

      <p className="mt-10 border-t-4 border-double border-ink pt-4 text-sm">
        <span className="font-bold">Receipt chain: </span>
        <StatusTag kind="wait">Not connected</StatusTag> The benchmark record has its own
        fingerprint, shown below and checked by{" "}
        <code className="font-mono">make verify-benchmark</code>. The full chain (source, audit,
        fixes, order, webhook) arrives with the money and audit services.
      </p>
      <p data-static className="mt-2 break-all font-mono text-xs">
        Benchmark record fingerprint (SHA-256): {recorded.sourceSha256}
      </p>
    </div>
  );
}
