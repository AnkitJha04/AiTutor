export default function ChatPanel({ title, content }) {
  return (
    <div className="rounded-2xl border border-clay/40 bg-white/80 p-5">
      <div className="flex items-center justify-between">
        <h3 className="font-display text-lg">{title}</h3>
        <span className="text-xs uppercase tracking-[0.2em] text-moss">Grounded</span>
      </div>
      <p className="mt-3 text-sm text-ink/80 whitespace-pre-line">{content}</p>
    </div>
  );
}
