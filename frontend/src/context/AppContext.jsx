import { createContext, useContext, useMemo, useState } from "react";

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [selection, setSelection] = useState({
    className: "Class 9",
    subject: "Science",
    chapter: ""
  });

  const value = useMemo(() => ({ selection, setSelection }), [selection]);
  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppContext() {
  return useContext(AppContext);
}
