export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex items-start justify-center pt-[200px] px-6 pb-8">
      <div className="max-w-[394px] w-full">{children}</div>
    </div>
  );
}
