<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div>
        <p class="eyebrow">TravelOps</p>
        <h1>旅游线路规划系统</h1>
      </div>
      <nav>
        <button
          v-for="item in navItems"
          :key="item.key"
          :class="{ active: activePage === item.key }"
          type="button"
          @click="activePage = item.key"
        >
          <span>{{ item.icon }}</span>
          {{ item.label }}
        </button>
      </nav>
    </aside>

    <main>
      <header class="topbar">
        <div>
          <p class="eyebrow">线路运营工作台</p>
          <h2>{{ pageTitle }}</h2>
        </div>
        <button type="button" class="primary-action" @click="loadData">刷新数据</button>
      </header>

      <div v-if="loading" class="state">数据加载中...</div>
      <div v-else-if="error" class="state error">{{ error }}</div>
      <component
        v-else
        :is="activeComponent"
        :attractions="attractions"
        :routes="routes"
        :bookings="bookings"
        :notices="notices"
        :action-error="actionError"
        @booking-created="handleBookingCreated"
        @booking-restored="handleBookingRestored"
        @booking-cancelled="handleBookingCancelled"
        @clear-action-error="actionError = ''"
      />
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { travelApi } from "./api/travel";
import AttractionsPage from "./pages/AttractionsPage.vue";
import RoutesPage from "./pages/RoutesPage.vue";
import BookingsPage from "./pages/BookingsPage.vue";
import NoticesPage from "./pages/NoticesPage.vue";

const navItems = [
  { key: "routes", label: "线路设计", icon: "路" },
  { key: "attractions", label: "景点库", icon: "景" },
  { key: "bookings", label: "报名成团", icon: "团" },
  { key: "notices", label: "出行通知", icon: "知" },
];

const pageMap = {
  routes: RoutesPage,
  attractions: AttractionsPage,
  bookings: BookingsPage,
  notices: NoticesPage,
};

const activePage = ref("routes");
const loading = ref(true);
const error = ref("");
const actionError = ref("");
const attractions = ref([]);
const routes = ref([]);
const bookings = ref([]);
const notices = ref([]);

const activeComponent = computed(() => pageMap[activePage.value]);
const pageTitle = computed(() => navItems.find((item) => item.key === activePage.value)?.label);

function parseErrorMessage(err) {
  try {
    const data = JSON.parse(err.message);
    if (data.detail) return data.detail;
    if (data.non_field_errors) return data.non_field_errors.join("；");
    if (typeof data === "string") return data;
    return err.message;
  } catch {
    return err.message || "操作失败，请稍后重试";
  }
}

function findBookingIndex(id) {
  return bookings.value.findIndex((b) => b.id === id);
}

function findRouteIndex(id) {
  return routes.value.findIndex((r) => r.id === id);
}

function recalcRouteEnrolled(routeId) {
  const routeIdx = findRouteIndex(routeId);
  if (routeIdx === -1) return;
  const route = routes.value[routeIdx];
  const routeBookings = bookings.value.filter(
    (b) => b.route === routeId && b.status !== "cancelled"
  );
  const enrolled = routeBookings.reduce((sum, b) => sum + b.party_size, 0);
  const progress = route.min_group_size === 0
    ? 100
    : Math.min(Math.round((enrolled / route.min_group_size) * 100), 100);
  route.enrolled_count = enrolled;
  route.group_progress = progress;

  bookings.value.forEach((b) => {
    if (b.route === routeId) {
      b.group_enrolled = enrolled;
      b.group_progress = progress;
    }
  });
}

async function loadData() {
  loading.value = true;
  error.value = "";
  try {
    const [attractionData, routeData, bookingData, noticeData] = await Promise.all([
      travelApi.getAttractions(),
      travelApi.getRoutes(),
      travelApi.getBookings(),
      travelApi.getNotices(),
    ]);
    attractions.value = attractionData;
    routes.value = routeData;
    bookings.value = bookingData;
    notices.value = noticeData;
  } catch (err) {
    error.value = `加载失败：${err.message}`;
  } finally {
    loading.value = false;
  }
}

async function handleBookingCreated(payload) {
  actionError.value = "";
  try {
    await travelApi.createBooking(payload);
    await loadData();
  } catch (err) {
    actionError.value = `提交报名失败：${parseErrorMessage(err)}`;
  }
}

async function handleBookingCancelled(bookingId) {
  actionError.value = "";
  const idx = findBookingIndex(bookingId);
  if (idx === -1) return;

  const booking = bookings.value[idx];
  const originalStatus = booking.status;
  const routeId = booking.route;

  booking.status = "cancelled";
  booking.status_label = "已取消";
  recalcRouteEnrolled(routeId);

  try {
    await travelApi.patchBooking(bookingId, { status: "cancelled" });
    await loadData();
  } catch (err) {
    booking.status = originalStatus;
    booking.status_label = originalStatus === "confirmed" ? "已确认" : "待确认";
    recalcRouteEnrolled(routeId);
    actionError.value = `取消报名失败：${parseErrorMessage(err)}`;
  }
}

async function handleBookingRestored(bookingId) {
  actionError.value = "";
  const idx = findBookingIndex(bookingId);
  if (idx === -1) return;

  const booking = bookings.value[idx];
  const originalStatus = booking.status;
  const routeId = booking.route;

  booking.status = "confirmed";
  booking.status_label = "已确认";
  recalcRouteEnrolled(routeId);

  try {
    await travelApi.patchBooking(bookingId, { status: "confirmed" });
    await loadData();
  } catch (err) {
    booking.status = originalStatus;
    booking.status_label = "已取消";
    recalcRouteEnrolled(routeId);
    actionError.value = `恢复报名失败：${parseErrorMessage(err)}`;
  }
}

onMounted(loadData);
</script>
