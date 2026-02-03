import math

class Service:
    def __init__(self, base, lower_rate, upper_rate, slab_limit,
                 threshold, discount):
        self.base = base
        self.lower_rate = lower_rate
        self.upper_rate = upper_rate
        self.slab_limit = slab_limit
        self.threshold = threshold
        self.discount = discount

    def calculate_distance_charge(self, distance):
        total = self.base
        slabs = math.ceil(distance / 2)

        lower_slabs = min(slabs, self.slab_limit // 2)
        upper_slabs = max(0, slabs - lower_slabs)

        total += lower_slabs * self.lower_rate
        total += upper_slabs * self.upper_rate

        return total

    def apply_threshold_discount(self, amount):
        if amount > self.threshold:
            amount -= amount * self.discount
        return amount

    def calculate_total_bill(self, distance, is_returning):
        amount = self.calculate_distance_charge(distance)
        amount = self.apply_threshold_discount(amount)

        if is_returning:
            amount -= amount * 0.05  # 5% loyalty discount

        return round(amount, 2)


class ServiceA(Service):
    def __init__(self):
        super().__init__(5, 1, 2, 10, 50, 0.10)


class ServiceB(Service):
    def __init__(self):
        super().__init__(10, 2, 3, 15, 75, 0.15)


class ServiceC(Service):
    def __init__(self):
        super().__init__(15, 3, 4, 20, 100, 0.20)


class ServiceD(Service):
    def __init__(self):
        super().__init__(20, 4, 5, 25, 125, 0.25)


# ----------- Usage Example ------------

service_map = {
    "A": ServiceA(),
    "B": ServiceB(),
    "C": ServiceC(),
    "D": ServiceD()
}

service_type = "A"
distance = 25
is_returning_customer = True

service = service_map[service_type]
bill = service.calculate_total_bill(distance, is_returning_customer)

print("Total Bill: $", bill)
