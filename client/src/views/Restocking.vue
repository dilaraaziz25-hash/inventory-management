<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <!-- Budget Card -->
    <div class="card">
      <div class="card-header">
        <h3 class="card-title">{{ t('restocking.budgetLabel') }}: {{ formatMoney(budget) }}</h3>
      </div>
      <div class="budget-controls">
        <input
          type="range"
          class="budget-slider"
          :min="minBudget"
          :max="maxBudget"
          :step="budgetStep"
          v-model.number="budget"
        />
        <input
          type="number"
          class="budget-number"
          :min="minBudget"
          :max="maxBudget"
          :step="budgetStep"
          v-model.number="budget"
        />
      </div>
      <div class="budget-help">
        {{ currencySymbol }}{{ minBudget.toLocaleString() }} – {{ currencySymbol }}{{ maxBudget.toLocaleString() }}
      </div>
    </div>

    <!-- Recommendations Card -->
    <div class="card">
      <div class="card-header">
        <div>
          <h3 class="card-title">{{ t('restocking.recommendationsTitle') }}</h3>
          <p v-if="recommendations.length > 0" class="card-subtitle">
            {{ t('restocking.selectedCount', { count: recommendations.length }) }}
          </p>
        </div>
      </div>

      <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
      <div v-else-if="error" class="error">{{ error }}</div>
      <div v-else-if="recommendations.length === 0" class="no-data">
        {{ t('restocking.noRecommendations') }}
      </div>
      <div v-else>
        <div class="table-container">
          <table class="restock-table">
            <thead>
              <tr>
                <th class="col-include">{{ t('restocking.table.include') }}</th>
                <th class="col-sku">{{ t('restocking.table.sku') }}</th>
                <th class="col-name">{{ t('restocking.table.name') }}</th>
                <th class="col-trend">{{ t('restocking.table.trend') }}</th>
                <th class="col-qty">{{ t('restocking.table.suggestedQty') }}</th>
                <th class="col-unit-cost">{{ t('restocking.table.unitCost') }}</th>
                <th class="col-line-total">{{ t('restocking.table.lineTotal') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="rec in recommendations" :key="rec.sku">
                <td class="col-include">
                  <input type="checkbox" v-model="selectedSkus[rec.sku]" />
                </td>
                <td class="col-sku"><code>{{ rec.sku }}</code></td>
                <td class="col-name">{{ rec.name }}</td>
                <td class="col-trend">
                  <span :class="['badge', rec.trend]">{{ t('trends.' + rec.trend) }}</span>
                </td>
                <td class="col-qty">{{ rec.suggested_quantity.toLocaleString() }}</td>
                <td class="col-unit-cost">
                  {{ formatMoney(rec.unit_cost) }}
                  <span v-if="rec.price_estimated" class="est-chip">{{ t('restocking.estimated') }}</span>
                </td>
                <td class="col-line-total">{{ formatMoney(rec.line_total) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Footer bar -->
        <div class="restock-footer">
          <div class="footer-stats">
            <div class="footer-stat">
              <span class="footer-stat-label">{{ t('restocking.selectedCount', { count: selectedCount }) }}</span>
            </div>
            <div class="footer-stat">
              <span class="footer-stat-label">{{ t('restocking.selectedTotal') }}:</span>
              <span class="footer-stat-value">{{ formatMoney(selectedTotal) }}</span>
            </div>
            <div class="footer-stat">
              <span class="footer-stat-label">{{ t('restocking.remainingBudget') }}:</span>
              <span class="footer-stat-value" :class="{ 'over-budget': remainingBudget < 0 }">{{ formatMoney(remainingBudget) }}</span>
            </div>
          </div>
          <button
            class="btn-primary"
            :disabled="selectedCount === 0 || submitting || selectedTotal > budget"
            @click="submitOrder"
          >
            {{ submitting ? t('common.loading') : t('restocking.placeOrder') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Confirmation Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="lastSubmittedOrder" class="modal-overlay" @click="closeModal">
          <div class="modal-container" @click.stop>
            <div class="modal-header">
              <h3 class="modal-title">{{ t('restocking.confirmTitle') }}</h3>
              <button class="close-button" @click="closeModal">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                </svg>
              </button>
            </div>
            <div class="modal-body">
              <div class="confirm-detail">
                <span class="confirm-label">{{ t('restocking.orderNumber') }}:</span>
                <span class="confirm-value order-number">{{ lastSubmittedOrder.order_number }}</span>
              </div>
              <p class="confirm-body">{{ t('restocking.confirmBody') }}</p>
              <div class="confirm-detail">
                <span class="confirm-label">{{ t('restocking.expectedDelivery') }}:</span>
                <span class="confirm-value">{{ formatDate(lastSubmittedOrder.expected_delivery) }}</span>
              </div>
            </div>
            <div class="modal-footer">
              <button class="btn-secondary" @click="closeModal">{{ t('common.close') }}</button>
              <router-link to="/orders" class="btn-primary" @click="closeModal">
                {{ t('restocking.viewInOrders') }}
              </router-link>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, reactive } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, currentLocale } = useI18n()

    const currencySymbol = computed(() => currentCurrency.value === 'JPY' ? '¥' : '$')

    const minBudget = 1000
    const maxBudget = 200000
    const budgetStep = 1000

    const budget = ref(25000)
    const recommendations = ref([])
    const selectedSkus = reactive({})
    const loading = ref(false)
    const error = ref(null)
    const submitting = ref(false)
    const lastSubmittedOrder = ref(null)

    let debounceTimer = null

    const formatMoney = (value) =>
      `${currencySymbol.value}${Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })}`

    const formatDate = (isoDate) => {
      if (!isoDate) return ''
      const date = new Date(isoDate)
      if (isNaN(date.getTime())) return ''
      const locale = currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'
      return date.toLocaleDateString(locale, { year: 'numeric', month: 'short', day: 'numeric' })
    }

    const loadRecommendations = async () => {
      loading.value = true
      error.value = null
      try {
        const data = await api.getRestockingRecommendations(budget.value)
        recommendations.value = data.recommendations || []
        // Reset selectedSkus — check all by default
        Object.keys(selectedSkus).forEach(k => delete selectedSkus[k])
        recommendations.value.forEach(rec => {
          selectedSkus[rec.sku] = true
        })
      } catch (err) {
        error.value = err.response?.data?.detail || 'Failed to load recommendations'
        recommendations.value = []
      } finally {
        loading.value = false
      }
    }

    watch(budget, () => {
      clearTimeout(debounceTimer)
      debounceTimer = setTimeout(() => {
        loadRecommendations()
      }, 250)
    })

    const selectedRecommendations = computed(() =>
      recommendations.value.filter(r => selectedSkus[r.sku] === true)
    )

    const selectedCount = computed(() => selectedRecommendations.value.length)

    const selectedTotal = computed(() =>
      selectedRecommendations.value.reduce((sum, r) => sum + r.line_total, 0)
    )

    const remainingBudget = computed(() => budget.value - selectedTotal.value)

    const submitOrder = async () => {
      if (selectedCount.value === 0 || submitting.value || selectedTotal.value > budget.value) return
      submitting.value = true
      error.value = null
      try {
        const payload = {
          items: selectedRecommendations.value.map(r => ({
            sku: r.sku,
            name: r.name,
            quantity: r.suggested_quantity,
            unit_price: r.unit_cost
          }))
        }
        const result = await api.submitRestockingOrder(payload)
        lastSubmittedOrder.value = result
      } catch (err) {
        error.value = err.response?.data?.detail || 'Failed to submit order'
      } finally {
        submitting.value = false
      }
    }

    const closeModal = () => {
      lastSubmittedOrder.value = null
    }

    onMounted(() => loadRecommendations())

    return {
      t,
      currencySymbol,
      minBudget,
      maxBudget,
      budgetStep,
      budget,
      recommendations,
      selectedSkus,
      loading,
      error,
      submitting,
      lastSubmittedOrder,
      selectedRecommendations,
      selectedCount,
      selectedTotal,
      remainingBudget,
      formatMoney,
      formatDate,
      submitOrder,
      closeModal
    }
  }
}
</script>

<style scoped>
.restocking {
  padding-bottom: 2rem;
}

/* Budget controls */
.budget-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.budget-slider {
  flex: 1;
  height: 6px;
  cursor: pointer;
  accent-color: #2563eb;
}

.budget-number {
  width: 130px;
  padding: 0.5rem 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.875rem;
  color: #0f172a;
  font-family: inherit;
}

.budget-number:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.budget-help {
  font-size: 0.813rem;
  color: #64748b;
  margin-top: 0.25rem;
}

/* Card subtitle */
.card-subtitle {
  font-size: 0.813rem;
  color: #64748b;
  margin-top: 0.25rem;
}

/* No data state */
.no-data {
  text-align: center;
  padding: 3rem;
  color: #64748b;
  font-size: 0.938rem;
}

/* Table columns */
.restock-table {
  width: 100%;
}

.col-include {
  width: 60px;
  text-align: center;
}

.col-sku {
  width: 110px;
}

.col-name {
  min-width: 180px;
}

.col-trend {
  width: 120px;
}

.col-qty {
  width: 120px;
  text-align: right;
}

.col-unit-cost {
  width: 150px;
  text-align: right;
}

.col-line-total {
  width: 130px;
  text-align: right;
}

.restock-table td.col-include {
  text-align: center;
}

.restock-table td.col-qty,
.restock-table td.col-unit-cost,
.restock-table td.col-line-total {
  text-align: right;
}

code {
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 0.813rem;
  color: #2563eb;
  background: #eff6ff;
  padding: 0.125rem 0.375rem;
  border-radius: 4px;
}

.est-chip {
  display: inline-block;
  margin-left: 0.375rem;
  padding: 0.125rem 0.375rem;
  background: #fef9c3;
  color: #854d0e;
  font-size: 0.688rem;
  font-weight: 600;
  border-radius: 4px;
  border: 1px solid #fde047;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

/* Footer bar */
.restock-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 0.75rem 0;
  border-top: 1px solid #e2e8f0;
  margin-top: 0.75rem;
  gap: 1rem;
  flex-wrap: wrap;
}

.footer-stats {
  display: flex;
  gap: 1.5rem;
  flex-wrap: wrap;
}

.footer-stat {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.footer-stat-label {
  font-size: 0.875rem;
  color: #64748b;
  font-weight: 500;
}

.footer-stat-value {
  font-size: 0.938rem;
  font-weight: 700;
  color: #0f172a;
}

.footer-stat-value.over-budget {
  color: #dc2626;
}

/* Primary button */
.btn-primary {
  padding: 0.625rem 1.5rem;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
}

.btn-primary:hover:not(:disabled) {
  background: #1d4ed8;
}

.btn-primary:disabled {
  background: #cbd5e1;
  color: #94a3b8;
  cursor: not-allowed;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 1rem;
}

.modal-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.15);
  max-width: 520px;
  width: 100%;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.close-button {
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  padding: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.close-button:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.modal-body {
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.confirm-detail {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.confirm-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  min-width: 140px;
}

.confirm-value {
  font-size: 0.938rem;
  font-weight: 600;
  color: #0f172a;
}

.confirm-value.order-number {
  font-family: 'Monaco', 'Courier New', monospace;
  color: #2563eb;
  font-size: 1rem;
}

.confirm-body {
  font-size: 0.938rem;
  color: #475569;
  line-height: 1.6;
}

.modal-footer {
  padding: 1.25rem 1.5rem;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.btn-secondary {
  padding: 0.625rem 1.25rem;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.875rem;
  color: #334155;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.btn-secondary:hover {
  background: #e2e8f0;
  border-color: #cbd5e1;
}

/* Modal transition */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-container,
.modal-leave-active .modal-container {
  transition: transform 0.2s ease;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: scale(0.95);
}

/* Narrow width adjustments */
@media (max-width: 900px) {
  .budget-controls {
    flex-direction: column;
    align-items: stretch;
  }

  .budget-number {
    width: 100%;
  }

  .restock-footer {
    flex-direction: column;
    align-items: flex-start;
  }

  .btn-primary {
    width: 100%;
    justify-content: center;
  }
}
</style>
