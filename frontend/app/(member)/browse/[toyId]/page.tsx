import { ToyDetail } from "@/components/toy-detail";

export default async function ToyDetailPage({
  params,
}: {
  params: Promise<{ toyId: string }>;
}) {
  const { toyId } = await params;
  return <ToyDetail toyId={toyId} />;
}
