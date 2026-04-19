import { Outlet } from "react-router-dom";
import { TopNav } from "./TopNav";

export function Layout() {
  return (
    <div className="min-h-screen bg-[#0a0a0a] text-white">
      <TopNav />
      <main className="max-w-7xl mx-auto px-6 py-6">
        <Outlet />
      </main>
    </div>
  );
}
