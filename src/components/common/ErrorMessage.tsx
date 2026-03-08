import { AlertCircle } from 'lucide-react';

interface ErrorMessageProps {
  message: string;
}

export default function ErrorMessage({ message }: ErrorMessageProps) {
  return (
    <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4 flex items-start gap-3 text-red-400">
      <AlertCircle className="w-5 h-5 mt-0.5 shrink-0" />
      <div>
        <h3 className="text-sm font-semibold">Orchestration Error</h3>
        <p className="text-xs text-red-400/80 mt-1">{message}</p>
      </div>
    </div>
  );
}
