import { fixtureProducts } from "@/lib/fixtures/products";

/** Placeholder demo store (owner: P3). Shows the deliberately messy fixture data for now. */
export default function DemoStore() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-12">
      <h1 className="text-2xl font-bold">Tidewell Goods (fictional demo store)</h1>
      <ul className="mt-6 space-y-4">
        {fixtureProducts.map((p) => (
          <li key={p.id} className="rounded border p-4">
            <h2 className="font-semibold">{p.name}</h2>
            <p className="mt-1">{p.description}</p>
            <p className="mt-1 font-medium">{p.priceText ?? "price on request"}</p>
          </li>
        ))}
      </ul>
    </main>
  );
}
