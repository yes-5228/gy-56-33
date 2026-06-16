<template>
  <section class="booking-layout">
    <form class="booking-form" @submit.prevent="submit">
      <div>
        <p class="eyebrow">Registration</p>
        <h3>新增报名</h3>
      </div>
      <label>
        选择线路
        <select v-model.number="form.route" required>
          <option disabled value="">请选择</option>
          <option v-for="route in routes" :key="route.id" :value="route.id">{{ route.title }}</option>
        </select>
      </label>
      <div v-if="selectedRoute" class="capacity-hint">
        已报 {{ selectedRoute.enrolled_count }} / 最多 {{ selectedRoute.max_group_size }} 人
      </div>
      <label>
        联系人
        <input v-model="form.contact_name" required />
      </label>
      <label>
        手机号
        <input v-model="form.phone" required />
      </label>
      <div class="form-row">
        <label>
          人数
          <input v-model.number="form.party_size" min="1" type="number" required />
        </label>
        <label>
          出行日期
          <input v-model="form.travel_date" type="date" required />
        </label>
      </div>
      <label>
        备注
        <textarea v-model="form.remark" rows="3"></textarea>
      </label>
      <p v-if="submitError" class="error-msg">{{ submitError }}</p>
      <button class="primary-action" type="submit" :disabled="submitting">
        {{ submitting ? "提交中..." : "提交报名" }}
      </button>
    </form>

    <section class="table-panel">
      <div class="panel-head">
        <div>
          <p class="eyebrow">Group Status</p>
          <h3>报名与成团状态</h3>
        </div>
        <span>{{ bookings.length }} 条报名</span>
      </div>
      <div v-if="actionError" class="action-error-banner">
        <span>{{ actionError }}</span>
        <button type="button" class="close-error" @click="$emit('clear-action-error')">×</button>
      </div>
      <div class="booking-list">
        <article v-for="booking in bookings" :key="booking.id">
          <div>
            <h4>{{ booking.contact_name }} · {{ booking.party_size }} 人</h4>
            <p>{{ booking.route_title }} / {{ booking.travel_date }}</p>
          </div>
          <div class="booking-actions">
            <span class="tag" :class="booking.status">{{ booking.status_label }}</span>
            <button
              v-if="booking.status !== 'cancelled'"
              class="cancel-btn"
              type="button"
              :disabled="booking._loading"
              @click="cancelBooking(booking)"
            >取消报名</button>
            <button
              v-else
              class="restore-btn"
              type="button"
              :disabled="booking._loading"
              @click="restoreBooking(booking)"
            >恢复报名</button>
          </div>
          <strong>{{ booking.group_enrolled }}/{{ booking.min_group_size }}人 · 进度{{ booking.group_progress }}%</strong>
        </article>
      </div>
    </section>
  </section>
</template>

<script setup>
import { computed, reactive, ref } from "vue";

const props = defineProps({
  routes: { type: Array, required: true },
  bookings: { type: Array, required: true },
  actionError: { type: String, default: "" },
});

const emit = defineEmits([
  "booking-created",
  "booking-restored",
  "booking-cancelled",
  "clear-action-error",
]);

const form = reactive({
  route: "",
  contact_name: "",
  phone: "",
  party_size: 1,
  travel_date: "",
  status: "pending",
  remark: "",
});

const submitError = ref("");
const submitting = ref(false);

const selectedRoute = computed(() =>
  props.routes.find((r) => r.id === form.route)
);

function submit() {
  submitError.value = "";
  if (selectedRoute.value) {
    const remaining = selectedRoute.value.max_group_size - selectedRoute.value.enrolled_count;
    if (form.party_size > remaining) {
      submitError.value = `名额不足：剩余 ${remaining} 人，本单报 ${form.party_size} 人`;
      return;
    }
  }
  submitting.value = true;
  emit("booking-created", { ...form });
  form.contact_name = "";
  form.phone = "";
  form.party_size = 1;
  form.travel_date = "";
  form.remark = "";
  submitting.value = false;
}

function cancelBooking(booking) {
  booking._loading = true;
  emit("booking-cancelled", booking.id);
}

function restoreBooking(booking) {
  booking._loading = true;
  emit("booking-restored", booking.id);
}
</script>
