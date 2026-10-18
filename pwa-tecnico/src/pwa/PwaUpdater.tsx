import { UpdateBanner } from "./UpdateBanner";
import { useAppUpdate } from "./useAppUpdate";

// Conecta el estado del service worker con el aviso visual.
export function PwaUpdater() {
  const { needRefresh, update } = useAppUpdate();

  return <UpdateBanner show={needRefresh} onUpdate={update} />;
}
