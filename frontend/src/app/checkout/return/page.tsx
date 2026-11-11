export const metadata = { title: "Payment approved · ShelfReady" };

export default function CheckoutReturn() {
  return (
    <main className="mx-auto max-w-xl px-4 py-16">
      <h1 className="font-display text-5xl font-bold tracking-tight">Payment approved</h1>
      <p className="mt-4">
        Thanks. PayPal told the store you approved the payment. The store now checks the order
        against its rules. If it is inside the limits it is captured right away; otherwise the
        seller approves it first. Sandbox only: no real money moves.
      </p>
    </main>
  );
}
