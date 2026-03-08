import { Loader2 } from 'lucide-react';

export default function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center h-full text-blue-400">
      <Loader2 className="animate-spin w-8 h-8" />
    </div>
  );
}
