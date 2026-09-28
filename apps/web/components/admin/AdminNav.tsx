import { Link } from "@/i18n/navigation";
import styles from "./AdminNav.module.css";

export interface AdminNavLabels {
  dashboard: string;
  changeRecords: string;
  verification: string;
  sources: string;
}

export function AdminNav({ labels }: { labels: AdminNavLabels }) {
  return (
    <nav aria-label="Admin sections" className={styles.nav}>
      <Link href="/admin" className={styles.link}>
        {labels.dashboard}
      </Link>
      <Link href="/admin/change-records" className={styles.link}>
        {labels.changeRecords}
      </Link>
      <Link href="/admin/verification" className={styles.link}>
        {labels.verification}
      </Link>
      <Link href="/admin/sources" className={styles.link}>
        {labels.sources}
      </Link>
    </nav>
  );
}
