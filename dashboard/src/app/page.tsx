import { redirect } from "next/navigation";

export default function RootPage() {
  // AuthGuard in /dashboard layout handles redirect to /login if no token
  redirect("/dashboard");
}
