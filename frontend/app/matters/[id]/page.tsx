import { redirect } from "next/navigation";

/**
 * The standalone full-page Matter view (Activity log, breadcrumb, sticky
 * header) was discarded by request — every Matter now opens in the /matters
 * master-detail panel instead (MatterDetailPanel). This route stays only so
 * old links/bookmarks to /matters/{id} still land somewhere real, rather
 * than 404ing.
 */
export default async function MatterDetailRedirect({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  redirect(`/matters?selected=${id}`);
}
