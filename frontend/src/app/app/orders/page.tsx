import { AdminGate } from "@/components/admin/use-admin";
import { OrdersView } from "@/components/admin/orders-view";

export const metadata = { title: "Orders · ShelfReady" };

export default function Page() {
  return (
    <div>
      <h1 className="font-display text-6xl font-bold leading-none tracking-tight">Orders</h1>
      <p className="mt-3 mb-6 max-w-2xl">
        Every agent order, the pipeline that decided it, and the orders waiting for your approval.
        Only code decides; you approve or reject.
      </p>
      <AdminGate>
        <OrdersView />
      </AdminGate>
    </div>
  );
}
