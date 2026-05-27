import { Dashboard } from "@/components/dashboard";
import { getDashboardData } from "@/lib/data";

export default function Home() {
  const data = getDashboardData();
  return <Dashboard data={data} />;
}
