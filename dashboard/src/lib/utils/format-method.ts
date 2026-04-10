import { METHOD_CONFIG } from "@/lib/constants";

export type CollectionMethod = "CARD" | "DEBIT_ORDER" | "MOBILE_MONEY";

export function getMethodConfig(method: CollectionMethod) {
  return METHOD_CONFIG[method];
}
