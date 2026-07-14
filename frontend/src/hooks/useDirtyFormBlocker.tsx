import { useEffect, useRef, useState } from "react";
import { useBlocker, type Blocker } from "react-router-dom";

interface Result {
  blocker: Blocker;
  open: boolean;
  proceed: () => void;
  cancel: () => void;
}

export function useDirtyFormBlocker(
  isDirty: boolean,
  shouldBypass?: () => boolean,
): Result {
  // Keep isDirty in a ref so the blocker callback always reads the latest
  // value synchronously. Without this, React batching can cause the callback
  // (closure-captured at register time) to see stale isDirty=true even after
  // setUserInteracted(false) + savingRef toggle in onSuccess handlers.
  const isDirtyRef = useRef(isDirty);
  isDirtyRef.current = isDirty;
  const bypassRef = useRef(shouldBypass);
  bypassRef.current = shouldBypass;

  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) => {
      if (bypassRef.current?.()) return false;
      return isDirtyRef.current && currentLocation.pathname !== nextLocation.pathname;
    },
  );
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (blocker.state === "blocked") setOpen(true);
  }, [blocker.state]);

  function proceed() {
    setOpen(false);
    if (blocker.state === "blocked") blocker.proceed();
  }

  function cancel() {
    setOpen(false);
    if (blocker.state === "blocked") blocker.reset();
  }

  return { blocker, open, proceed, cancel };
}
